#!/usr/bin/env python3
"""
BrailleVision -- held-out evaluation (exact-match % + character error rate).

Usage:   python evaluate.py path/to/best.pt
Expects: a  test/  folder of images and  test/labels.csv  with columns:
             filename,truth
         e.g.    img01.jpg,hello
Run it on Account A's and Account B's weights, ship the better one.
"""

import csv
import os
import sys

import cv2
import numpy as np
from ultralytics import YOLO


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


def cer(ref, hyp):
    """Character error rate = edit distance / len(reference)."""
    m, n = len(ref), len(hyp)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev = cur
    return dp[n] / max(1, m)


def main():
    weights = sys.argv[1] if len(sys.argv) > 1 else "best.pt"
    model = YOLO(weights)
    names = model.names
    rows = list(csv.DictReader(open("test/labels.csv")))
    tot, exact = 0.0, 0
    for r in rows:
        img = cv2.imread(os.path.join("test", r["filename"]))
        if img is None:
            print("MISSING:", r["filename"])
            continue
        res = model.predict(img, conf=0.35, verbose=False)[0]
        dets = []
        for b in res.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            dets.append(((x1 + x2) / 2, (y1 + y2) / 2, names[int(b.cls[0])], y2 - y1))
        pred = reading_order(dets).replace("\n", " ").strip()
        truth = r["truth"].strip()
        c = cer(truth, pred)
        tot += c
        exact += int(pred == truth)
        print(f'{r["filename"]:22s} truth="{truth}"  pred="{pred}"  CER={c:.2f}')
    n = max(1, len(rows))
    print(f'\nN={len(rows)}  exact-match={exact / n:.0%}  mean-CER={tot / n:.2f}')


if __name__ == "__main__":
    main()
