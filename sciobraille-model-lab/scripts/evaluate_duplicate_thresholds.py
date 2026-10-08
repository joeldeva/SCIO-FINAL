#!/usr/bin/env python3
"""Evaluate duplicate IoU suppression thresholds on development validation data.

Compares duplicate_iou thresholds in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
across development samples without hardcoding or biasing toward the 3 physical images.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
REPORTS = LAB / "reports"
DATASETS = LAB / "datasets" / "master_v2"
V2_MODEL_PATH = LAB / "models" / "v2_master" / "best.pt"

import sys
sys.path.insert(0, str(LAB / "scripts"))
import tune_inference
from evaluate_text import text_metrics


def main() -> int:
    print("Loading V2 Model...")
    model = YOLO(str(V2_MODEL_PATH))
    names = model.names

    val_images = sorted((DATASETS / "images" / "val").glob("*.jpg"))[:25]
    print(f"Loaded {len(val_images)} development validation images.")

    base_cfg = tune_inference.Config(
        confidence=0.35,
        iou=0.45,
        preprocessing="current_production",
        flip_strategy="never",
    )

    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    results_by_thresh = {}

    for thresh in thresholds:
        cfg = tune_inference.Config(
            confidence=base_cfg.confidence,
            iou=base_cfg.iou,
            preprocessing=base_cfg.preprocessing,
            duplicate_handling="class_agnostic",
            duplicate_iou=thresh,
            flip_strategy="never",
        )
        total_boxes = []
        total_suppressed = 0
        total_raw = 0

        for img_path in val_images:
            img = cv2.imread(str(img_path))
            res = tune_inference.infer(model, names, img, cfg, metadata_flip=False)
            total_boxes.append(res["detections"])

        avg_boxes = float(np.mean(total_boxes))
        results_by_thresh[thresh] = {
            "avg_boxes_kept": round(avg_boxes, 2),
            "total_boxes_kept": int(np.sum(total_boxes)),
        }
        print(f"Threshold IoU={thresh:.2f}: Avg boxes/img={avg_boxes:.2f}, Total boxes={np.sum(total_boxes)}")

    # Check differences across thresholds
    print("\nThreshold Sensitivity Summary:")
    for thresh, data in results_by_thresh.items():
        delta = data["total_boxes_kept"] - results_by_thresh[0.70]["total_boxes_kept"]
        print(f"  IoU {thresh:.2f}: {data['total_boxes_kept']} boxes (Delta vs 0.70: {delta:+d})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
