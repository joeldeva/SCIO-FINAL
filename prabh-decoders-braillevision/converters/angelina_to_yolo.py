#!/usr/bin/env python3
"""
Convert the Angelina Braille Images Dataset (IlyaOvodov/AngelinaDataset)
from its native CSV annotation format to YOLO detection format.

Angelina CSV format per image:
    <image_filename>.labeled.csv with lines:  left;top;right;bottom;label
    Coordinates are normalized [0,1].
    Label is a bitmask integer where bit N-1 represents dot N being present.
    (dot 1 = bit 0, dot 2 = bit 1, ..., dot 6 = bit 5)

YOLO format:
    <class_id> <x_center> <y_center> <width> <height>

Usage:
    python converters/angelina_to_yolo.py --src datasets/AngelinaDataset --out datasets/angelina_yolo
"""

import argparse
import os
import shutil
import yaml

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

# Standard English Braille a-z (Grade 1)
CANON = list("abcdefghijklmnopqrstuvwxyz")
CIDX = {c: i for i, c in enumerate(CANON)}

# Build bitmask → English letter mapping
# Angelina encodes dots as: dot N → bit (N-1)
# So dot 1 = bit 0 = 1, dot 2 = bit 1 = 2, dot 3 = bit 2 = 4, etc.
# English Braille dot patterns:
EN_DOTS_TO_LETTER = {
    '1': 'a',     '12': 'b',    '14': 'c',    '145': 'd',
    '15': 'e',    '124': 'f',   '1245': 'g',  '125': 'h',
    '24': 'i',    '245': 'j',   '13': 'k',    '123': 'l',
    '134': 'm',   '1345': 'n',  '135': 'o',   '1234': 'p',
    '12345': 'q', '1235': 'r',  '234': 's',   '2345': 't',
    '136': 'u',   '1236': 'v',  '2456': 'w',  '1346': 'x',
    '13456': 'y', '1356': 'z',
}


def dots_string_to_bitmask(dots_str):
    """Convert a dot string like '1345' to bitmask integer."""
    mask = 0
    for ch in dots_str:
        dot = int(ch)
        mask |= (1 << (dot - 1))
    return mask


# Build bitmask integer → letter lookup
BITMASK_TO_LETTER = {}
for dots_str, letter in EN_DOTS_TO_LETTER.items():
    bitmask = dots_string_to_bitmask(dots_str)
    BITMASK_TO_LETTER[bitmask] = letter

# The Angelina dataset is primarily Russian, but the dot PATTERNS for
# dots 1-6 are universal. We map using English Braille because that's
# what our model needs. Note: same dots can mean different letters in
# different languages, but the CELL PATTERN is the same.
# For the detector, we just need the bounding boxes with a-z labels.


def bitmask_to_letter(label_int):
    """Convert Angelina's integer label to an English letter, or None."""
    return BITMASK_TO_LETTER.get(label_int)


def convert_angelina(src_dir, out_dir):
    """Convert Angelina dataset to YOLO format."""
    os.makedirs(os.path.join(out_dir, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "labels", "train"), exist_ok=True)

    converted = 0
    skipped_labels = {}
    total_boxes = 0

    # Walk through the dataset looking for image + CSV pairs
    # Angelina stores files as: <name>.labeled.jpg + <name>.labeled.csv
    for root, dirs, files in os.walk(src_dir):
        # Skip .git
        if '.git' in root:
            continue

        image_files = [f for f in files if f.lower().endswith(IMG_EXT)]
        for img_file in image_files:
            img_path = os.path.join(root, img_file)
            stem = os.path.splitext(img_file)[0]

            # Look for corresponding CSV
            csv_path = os.path.join(root, stem + ".csv")
            if not os.path.exists(csv_path):
                # Some files are like "01.labeled.jpg" with "01.labeled.csv"
                # Already handled since stem = "01.labeled"
                continue

            # Parse CSV annotations
            yolo_lines = []
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split(';')
                        if len(parts) < 5:
                            continue

                        try:
                            left = float(parts[0])
                            top = float(parts[1])
                            right = float(parts[2])
                            bottom = float(parts[3])
                            label_int = int(parts[4])
                        except (ValueError, IndexError):
                            continue

                        # Convert bitmask to English letter
                        letter = bitmask_to_letter(label_int)
                        if letter is None:
                            skipped_labels[label_int] = skipped_labels.get(label_int, 0) + 1
                            continue

                        # Coords are already normalized [0,1]
                        x_center = (left + right) / 2.0
                        y_center = (top + bottom) / 2.0
                        width = right - left
                        height = bottom - top

                        # Sanity check
                        if width <= 0 or height <= 0:
                            continue
                        if x_center < 0 or y_center < 0 or x_center > 1 or y_center > 1:
                            continue

                        class_id = CIDX[letter]
                        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                        total_boxes += 1
            except Exception as e:
                print(f"  [warn] Error reading {csv_path}: {e}")
                continue

            if not yolo_lines:
                continue

            # Copy image and write label
            # Create a unique filename to avoid collisions
            safe_stem = stem.replace("/", "_").replace("\\", "_")
            out_stem = f"angelina_{converted}_{safe_stem}"
            ext = os.path.splitext(img_file)[1].lower()
            shutil.copy(img_path, os.path.join(out_dir, "images", "train", out_stem + ext))
            with open(os.path.join(out_dir, "labels", "train", out_stem + ".txt"), "w") as f:
                f.write("\n".join(yolo_lines))
            converted += 1

    # Write data.yaml
    with open(os.path.join(out_dir, "data.yaml"), "w") as f:
        yaml.safe_dump({
            "path": os.path.abspath(out_dir),
            "train": "images/train",
            "val": "images/train",  # merge_datasets.py handles the split
            "nc": 26,
            "names": CANON
        }, f, sort_keys=False)

    print(f"\n=== Angelina Conversion Complete ===")
    print(f"  Converted: {converted} images, {total_boxes} boxes")
    if skipped_labels:
        print(f"  Skipped bitmask labels (non a-z): {dict(sorted(skipped_labels.items(), key=lambda x: -x[1]))}")
        # Show what these bitmasks mean
        print(f"  (These are punctuation, numbers, caps signs, etc.)")
    print(f"  Output: {out_dir}/")
    return converted


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert Angelina dataset to YOLO format")
    ap.add_argument("--src", default="datasets/AngelinaDataset", help="Path to cloned AngelinaDataset repo")
    ap.add_argument("--out", default="datasets/angelina_yolo", help="Output YOLO dataset directory")
    args = ap.parse_args()
    convert_angelina(args.src, args.out)
