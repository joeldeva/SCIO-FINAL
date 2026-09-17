"""
BrailleVision - Generate Sample Braille Test Images
Creates synthetic Braille images for testing when real physical images aren't available.
Run: python generate_samples.py
"""

import cv2
import numpy as np
import os
import json
from pathlib import Path

# Braille dot positions in a 2x3 cell grid (dot_num: (col, row) in 0-indexed)
DOT_POSITIONS = {
    1: (0, 0), 2: (0, 1), 3: (0, 2),
    4: (1, 0), 5: (1, 1), 6: (1, 2)
}

BRAILLE_PATTERNS = {
    'a': [1], 'b': [1,2], 'c': [1,4], 'd': [1,4,5], 'e': [1,5],
    'f': [1,2,4], 'g': [1,2,4,5], 'h': [1,2,5], 'i': [2,4], 'j': [2,4,5],
    'k': [1,3], 'l': [1,2,3], 'm': [1,3,4], 'n': [1,3,4,5], 'o': [1,3,5],
    'p': [1,2,3,4], 'q': [1,2,3,4,5], 'r': [1,2,3,5], 's': [2,3,4], 't': [2,3,4,5],
    'u': [1,3,6], 'v': [1,2,3,6], 'w': [2,4,5,6], 'x': [1,3,4,6],
    'y': [1,3,4,5,6], 'z': [1,3,5,6]
}

OUTPUT_DIR = Path("dataset/sample_inputs")
ANNOTATIONS_DIR = Path("dataset/sample_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)


def draw_braille_cell(img, x, y, dots, cell_w=60, cell_h=80, 
                       dot_radius=7, color=(220, 220, 220), 
                       raised_color=(100, 100, 100)):
    """Draw a single Braille cell at position (x,y)."""
    dot_pad_x = cell_w // 4
    dot_pad_y = cell_h // 6
    dot_spacing_x = (cell_w - 2 * dot_pad_x) // 1
    dot_spacing_y = (cell_h - 2 * dot_pad_y) // 2

    for dot_num, (col, row) in DOT_POSITIONS.items():
        cx = x + dot_pad_x + col * dot_spacing_x
        cy = y + dot_pad_y + row * dot_spacing_y

        if dot_num in dots:
            # Raised dot - darker, with shadow effect
            cv2.circle(img, (cx+1, cy+1), dot_radius, (60, 60, 60), -1)  # shadow
            cv2.circle(img, (cx, cy), dot_radius, raised_color, -1)
            cv2.circle(img, (cx-1, cy-1), dot_radius//2, (140, 140, 140), -1)  # highlight
        else:
            # Flat position - very subtle indent
            cv2.circle(img, (cx, cy), dot_radius, (200, 200, 200), 1)


def generate_word_image(word: str, filename: str, style: str = "clean"):
    """Generate a Braille image for a word."""
    word = word.lower().strip()
    valid_chars = [c for c in word if c in BRAILLE_PATTERNS or c == ' ']
    if not valid_chars:
        return None

    cell_w, cell_h = 55, 75
    padding = 30
    gap = 15  # gap between cells

    # Image dimensions
    n_chars = len(valid_chars)
    img_w = padding * 2 + n_chars * (cell_w + gap)
    img_h = padding * 2 + cell_h

    # Create background
    if style == "clean":
        bg_color = (230, 228, 225)  # Paper-like
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * np.array(bg_color, dtype=np.uint8)
    elif style == "embossed":
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 215
        # Add texture noise
        noise = np.random.randint(-8, 8, img.shape, dtype=np.int8)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    else:
        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 240

    annotations = []

    for i, char in enumerate(valid_chars):
        if char == ' ':
            continue

        x = padding + i * (cell_w + gap)
        y = padding

        dots = BRAILLE_PATTERNS.get(char, [])
        draw_braille_cell(img, x, y, dots, cell_w, cell_h)

        # Add some embossed depth effect for realism
        if style == "embossed":
            region = img[y:y+cell_h, x:x+cell_w]
            blur = cv2.GaussianBlur(region, (3,3), 0)
            img[y:y+cell_h, x:x+cell_w] = blur

        annotations.append({
            "char": char,
            "dots": dots,
            "bbox": [x, y, cell_w, cell_h]
        })

    # Add slight overall blur for realism
    if style == "embossed":
        img = cv2.GaussianBlur(img, (3,3), 0.5)

    # Add lighting gradient (top-left brighter)
    if style == "embossed":
        gradient = np.zeros((img_h, img_w), dtype=np.float32)
        for gy in range(img_h):
            for gx in range(img_w):
                gradient[gy, gx] = 1.0 - (gx + gy) / (img_w + img_h) * 0.15
        gradient_3c = np.stack([gradient]*3, axis=2)
        img = np.clip(img.astype(np.float32) * gradient_3c, 0, 255).astype(np.uint8)

    # Save image
    img_path = OUTPUT_DIR / filename
    cv2.imwrite(str(img_path), img)

    # Save annotations
    ann_path = ANNOTATIONS_DIR / filename.replace('.jpg', '.json')
    with open(ann_path, 'w') as f:
        json.dump({
            "word": word,
            "image": filename,
            "cells": annotations,
            "style": style
        }, f, indent=2)

    print(f"  [OK] {filename} -> '{word}' ({len(annotations)} cells)")
    return str(img_path)


def generate_yolo_dataset():
    """Generate a mini YOLO-format dataset."""
    yolo_img_dir = Path("dataset/images/train")
    yolo_label_dir = Path("dataset/labels/train")
    yolo_val_img = Path("dataset/images/val")
    yolo_val_label = Path("dataset/labels/val")

    for d in [yolo_img_dir, yolo_label_dir, yolo_val_img, yolo_val_label]:
        d.mkdir(parents=True, exist_ok=True)

    words = ['hello', 'braille', 'vision', 'read', 'text', 'learn', 'help', 
             'world', 'ai', 'see', 'feel', 'touch', 'open', 'mind', 'hope']

    class_names = list('abcdefghijklmnopqrstuvwxyz')

    for i, word in enumerate(words):
        valid = [c for c in word.lower() if c in BRAILLE_PATTERNS]
        if not valid:
            continue

        cell_w, cell_h = 55, 75
        padding = 30
        gap = 15
        n_chars = len(valid)
        img_w = padding * 2 + n_chars * (cell_w + gap)
        img_h = padding * 2 + cell_h

        img = np.ones((img_h, img_w, 3), dtype=np.uint8) * 215
        noise = np.random.randint(-10, 10, img.shape, dtype=np.int8)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        labels = []
        for j, char in enumerate(valid):
            x = padding + j * (cell_w + gap)
            y = padding
            dots = BRAILLE_PATTERNS.get(char, [])
            draw_braille_cell(img, x, y, dots, cell_w, cell_h)

            cls_id = class_names.index(char)
            # YOLO format: class cx cy w h (normalized)
            cx = (x + cell_w / 2) / img_w
            cy = (y + cell_h / 2) / img_h
            nw = cell_w / img_w
            nh = cell_h / img_h
            labels.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        target_dir = yolo_img_dir if i < 12 else yolo_val_img
        label_dir = yolo_label_dir if i < 12 else yolo_val_label

        cv2.imwrite(str(target_dir / f"{word}.jpg"), img)
        with open(label_dir / f"{word}.txt", 'w') as f:
            f.write('\n'.join(labels))

    # Write data.yaml
    yaml_content = f"""path: ../dataset
train: images/train
val: images/val

nc: 26
names: {class_names}
"""
    with open("dataset/data.yaml", 'w') as f:
        f.write(yaml_content)

    print(f"\n[OK] YOLO dataset written to dataset/")
    print(f"   Train images: {len(list(yolo_img_dir.glob('*.jpg')))}")
    print(f"   Val images:   {len(list(yolo_val_img.glob('*.jpg')))}")


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    print("\n[*] BrailleVision - Generating Sample Dataset\n")
    print("[+] Generating sample input images...")

    test_words = [
        ("hello_clean.jpg", "hello", "clean"),
        ("braille_embossed.jpg", "braille", "embossed"),
        ("vision_clean.jpg", "vision", "clean"),
        ("help_embossed.jpg", "help", "embossed"),
        ("read_clean.jpg", "read", "clean"),
        ("ai_clean.jpg", "ai", "clean"),
        ("abcde_clean.jpg", "abcde", "clean"),
        ("world_embossed.jpg", "world", "embossed"),
    ]

    for fname, word, style in test_words:
        generate_word_image(word, fname, style)

    print("\n[+] Generating YOLO dataset...")
    generate_yolo_dataset()

    print("\n[DONE] Files saved to dataset/")
    print("   Run: python inference_cli.py --image dataset/sample_inputs/hello_clean.jpg")
