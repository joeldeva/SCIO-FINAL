#!/usr/bin/env python3
"""
BrailleVision -- offline inference on Braille image(s).

Judges (or anyone) can verify the model locally:

    python inference.py --source sample_inputs/test_braille.jpg --weights model/best.pt
    python inference.py --source sample_inputs/ --weights model/best.pt      # whole folder
    python inference.py --source img.jpg --no-enhance                        # skip preprocessing

For each image it prints the decoded Braille text and writes an annotated copy
plus a .txt of the reading to the output folder (default: sample_outputs/).

Preprocessing: bilateral filter (edge-preserving smoothing) + test-time augmentation (TTA)
are enabled by default for best accuracy on real-world Braille photos.
"""

import argparse
import glob
import os

import cv2
import numpy as np
from ultralytics import YOLO

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def reading_order(dets, line_tol_frac=0.6, space_mult=1.7):
    """dets: list of (cx, cy, label, box_height) -> text in reading order."""
    if not dets:
        return ""
    med_h = float(np.median([d[3] for d in dets]))
    dets = sorted(dets, key=lambda d: d[1])
    lines, cur = [], [dets[0]]
    for d in dets[1:]:
        if abs(d[1] - cur[-1][1]) <= med_h * line_tol_frac:
            cur.append(d)
        else:
            lines.append(cur)
            cur = [d]
    lines.append(cur)
    out = []
    for ln in lines:
        ln = sorted(ln, key=lambda d: d[0])
        s = ln[0][2]
        for prev, d in zip(ln, ln[1:]):
            if (d[0] - prev[0]) > med_h * space_mult:
                s += " "
            s += d[2]
        out.append(s)
    return "\n".join(out)


def preprocess(img, bilateral_d=9, bilateral_sigma=75):
    """Apply bilateral filter to enhance Braille dot visibility.
    
    Bilateral filtering smooths flat regions (paper texture/noise) while
    preserving sharp edges (dot boundaries), making dot detection cleaner.
    """
    return cv2.bilateralFilter(img, bilateral_d, bilateral_sigma, bilateral_sigma)


def decode_image(model, names, img, conf, enhance=True, augment=True):
    # Preprocess for better detection
    processed = preprocess(img) if enhance else img
    res = model.predict(processed, conf=conf, verbose=False, augment=augment)[0]
    annotated = img.copy()  # Draw boxes on original (not preprocessed) image
    dets = []
    for b in res.boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        label = names[int(b.cls[0])]
        dets.append(((x1 + x2) / 2, (y1 + y2) / 2, label, y2 - y1))
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 230, 0), 2)
        cv2.putText(annotated, label, (int(x1), int(y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)
    return reading_order(dets), annotated


def main():
    ap = argparse.ArgumentParser(description="BrailleVision offline inference")
    ap.add_argument("--source", required=True, help="image file or a folder of images")
    ap.add_argument("--weights", default="model/best.pt", help="path to trained weights (.pt)")
    ap.add_argument("--out", default="sample_outputs", help="output folder")
    ap.add_argument("--conf", type=float, default=0.35, help="confidence threshold")
    ap.add_argument("--no-enhance", action="store_true", help="skip bilateral filter preprocessing")
    ap.add_argument("--no-tta", action="store_true", help="skip test-time augmentation")
    args = ap.parse_args()

    if os.path.isdir(args.source):
        files = sorted(f for f in glob.glob(os.path.join(args.source, "*"))
                       if f.lower().endswith(IMG_EXT))
    else:
        files = [args.source]
    if not files:
        print("No images found at:", args.source)
        return

    os.makedirs(args.out, exist_ok=True)
    print("Loading model:", args.weights)
    model = YOLO(args.weights)
    names = model.names

    print(f"\nRunning inference on {len(files)} image(s):\n" + "-" * 60)
    for fp in files:
        img = cv2.imread(fp)
        if img is None:
            print("Skip (unreadable):", fp)
            continue
        text, annotated = decode_image(model, names, img, args.conf,
                                        enhance=not args.no_enhance,
                                        augment=not args.no_tta)
        base = os.path.splitext(os.path.basename(fp))[0]
        out_img = os.path.join(args.out, base + "_out.jpg")
        out_txt = os.path.join(args.out, base + "_out.txt")
        cv2.imwrite(out_img, annotated)
        with open(out_txt, "w") as f:
            f.write(text)
        shown = text.replace("\n", " / ") if text else "(nothing detected)"
        print(f'{os.path.basename(fp):28s} -> "{shown}"   [saved {out_img}]')
    print("-" * 60 + f"\nDone. Annotated images + .txt readings are in: {args.out}/")


if __name__ == "__main__":
    main()
