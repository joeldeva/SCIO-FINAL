#!/usr/bin/env python3
"""Investigate physical benchmark regression between V1 and V2.

Produces annotated visual comparisons and granular per-image error breakdowns:
- Raw text & Levenshtein error breakdown
- Detected vs missing vs duplicate cells
- Class recognition confusion
- Reading order & word spacing
- Confidence distributions
- Visual comparison images saved to reports/visualizations/physical_benchmark/
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
SCRIPTS = LAB / "scripts"
REPORTS = LAB / "reports"
VIS_DIR = REPORTS / "visualizations" / "physical_benchmark"
CONFIG_PATH = LAB / "configs" / "v1_optimized.yaml"
GT_PATH = LAB / "benchmark" / "ground_truth.csv"

V1_PATH = ROOT / "sciobraille-scanner" / "backend" / "model" / "best.pt"
V2_PATH = LAB / "models" / "v2_master" / "best.pt"

sys.path.insert(0, str(SCRIPTS))
import tune_inference
from evaluate_text import levenshtein, normalize_text, text_metrics


def draw_annotated_image(
    image: np.ndarray,
    detections: list[dict[str, Any]],
    title: str,
    raw_text: str,
    ground_truth: str,
    cer: float,
    wer: float,
) -> np.ndarray:
    """Draw bounding boxes, labels, confidences, and reading order annotations."""
    annotated = image.copy()
    h, w = annotated.shape[:2]

    # Create top header canvas for text info
    header_height = 140
    canvas = np.ones((h + header_height, w, 3), dtype=np.uint8) * 245
    canvas[header_height:, :] = annotated

    # Draw header text
    cv2.putText(canvas, title, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    gt_clean = ground_truth.replace("\n", " / ")
    pred_clean = raw_text.replace("\n", " / ") if raw_text else "(No detections)"
    cv2.putText(canvas, f"Ground Truth: {gt_clean}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 100, 10), 1)
    cv2.putText(canvas, f"Raw Pred:     {pred_clean}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 20, 20), 1)
    cv2.putText(canvas, f"Metrics:      CER={cer:.4f} | WER={wer:.4f} | Detections: {len(detections)}", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1)

    # Sort detections by y_center then x_center to establish reading order index
    sorted_dets = sorted(detections, key=lambda d: (d["y_center"] // 30, d["x_center"]))

    for idx, d in enumerate(sorted_dets, 1):
        x1, y1 = int(round(d["x1"])), int(round(d["y1"])) + header_height
        x2, y2 = int(round(d["x2"])), int(round(d["y2"])) + header_height
        label = d["label"]
        conf = d["confidence"]

        # Color based on confidence: high conf green, lower conf orange/red
        if conf >= 0.70:
            color = (30, 180, 30)
        elif conf >= 0.50:
            color = (0, 165, 255)
        else:
            color = (0, 0, 220)

        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        tag = f"#{idx} {label} {conf:.2f}"
        cv2.putText(canvas, tag, (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    return canvas


def infer_full(model: YOLO, names: dict[int, str], image: np.ndarray, config: tune_inference.Config, metadata_flip: bool) -> dict[str, Any]:
    candidates = []
    for flipped, oriented in tune_inference.orientation_candidates(image, config.flip_strategy, metadata_flip):
        model_input, fallback = tune_inference.preprocess(oriented, config.preprocessing)
        result = model.predict(
            model_input,
            conf=config.confidence,
            iou=config.iou,
            imgsz=config.imgsz,
            augment=config.tta,
            verbose=False,
        )[0]
        if fallback is not None and len(result.boxes) == 0:
            result = model.predict(
                fallback,
                conf=config.confidence,
                iou=config.iou,
                imgsz=config.imgsz,
                augment=config.tta,
                verbose=False,
            )[0]
        dets = tune_inference.parse_boxes(result, names)
        score = len(dets) * (float(np.mean([item["confidence"] for item in dets])) if dets else 0.0)
        candidates.append((score, flipped, oriented, dets))
    _, flipped, oriented, detections = max(candidates, key=lambda item: item[0])
    raw_text = tune_inference.reconstruct(detections, config)
    return {
        "raw_text": raw_text,
        "boxes": detections,
        "flipped": flipped,
        "oriented_image": oriented,
    }


def main() -> int:
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    cfg_data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["configuration"]
    config = tune_inference.Config(**cfg_data)
    samples = tune_inference.load_samples(GT_PATH)

    v1_model = YOLO(str(V1_PATH))
    v2_model = YOLO(str(V2_PATH))

    report_data = []

    print("=" * 70)
    print("INVESTIGATING PHYSICAL BENCHMARK REGRESSION (V1 vs V2)")
    print("=" * 70)

    for sample in samples:
        sample_id = sample["id"]
        gt_text = sample["ground_truth"]
        raw_image = sample["image"]
        meta_flip = sample["metadata_flip"]

        # Preprocess and infer V1
        v1_infer = infer_full(v1_model, v1_model.names, raw_image, config, meta_flip)
        v1_raw_text = v1_infer["raw_text"]
        v1_metrics = text_metrics(gt_text, v1_raw_text)

        # Preprocess and infer V2
        v2_infer = infer_full(v2_model, v2_model.names, raw_image, config, meta_flip)
        v2_raw_text = v2_infer["raw_text"]
        v2_metrics = text_metrics(gt_text, v2_raw_text)

        # Confidence analysis
        v1_confs = [d["confidence"] for d in v1_infer["boxes"]] or [0.0]
        v2_confs = [d["confidence"] for d in v2_infer["boxes"]] or [0.0]

        # Duplicate detection analysis (IoU >= duplicate_iou)
        def count_overlaps(dets: list[dict[str, Any]], thresh: float = 0.70) -> int:
            count = 0
            for i in range(len(dets)):
                for j in range(i + 1, len(dets)):
                    if tune_inference.box_iou(dets[i], dets[j]) >= thresh:
                        count += 1
            return count

        v1_dup = count_overlaps(v1_infer["boxes"])
        v2_dup = count_overlaps(v2_infer["boxes"])

        record = {
            "id": sample_id,
            "ground_truth": gt_text,
            "v1": {
                "raw_text": v1_raw_text,
                "cer": v1_metrics["cer"],
                "wer": v1_metrics["wer"],
                "char_errors": v1_metrics["char_distance"],
                "word_errors": v1_metrics["word_distance"],
                "detection_count": len(v1_infer["boxes"]),
                "duplicates_above_0.70": v1_dup,
                "mean_conf": float(np.mean(v1_confs)),
                "min_conf": float(np.min(v1_confs)),
                "max_conf": float(np.max(v1_confs)),
                "std_conf": float(np.std(v1_confs)),
                "boxes": v1_infer["boxes"],
            },
            "v2": {
                "raw_text": v2_raw_text,
                "cer": v2_metrics["cer"],
                "wer": v2_metrics["wer"],
                "char_errors": v2_metrics["char_distance"],
                "word_errors": v2_metrics["word_distance"],
                "detection_count": len(v2_infer["boxes"]),
                "duplicates_above_0.70": v2_dup,
                "mean_conf": float(np.mean(v2_confs)),
                "min_conf": float(np.min(v2_confs)),
                "max_conf": float(np.max(v2_confs)),
                "std_conf": float(np.std(v2_confs)),
                "boxes": v2_infer["boxes"],
            },
        }
        report_data.append(record)

        print(f"\n--- Sample: {sample_id} ---")
        print(f"Ground truth:      {gt_text.replace(chr(10), ' / ')}")
        print(f"V1 Raw Text:       {v1_raw_text.replace(chr(10), ' / ')} (CER={v1_metrics['cer']:.4f}, WER={v1_metrics['wer']:.4f}, Dets={len(v1_infer['boxes'])})")
        print(f"V2 Raw Text:       {v2_raw_text.replace(chr(10), ' / ')} (CER={v2_metrics['cer']:.4f}, WER={v2_metrics['wer']:.4f}, Dets={len(v2_infer['boxes'])})")

        # Generate visual annotated images
        img_for_vis = v1_infer["oriented_image"]  # image after optional horizontal flip
        v1_vis = draw_annotated_image(img_for_vis, v1_infer["boxes"], f"V1 Production ({sample_id})", v1_raw_text, gt_text, v1_metrics["cer"], v1_metrics["wer"])
        v2_vis = draw_annotated_image(img_for_vis, v2_infer["boxes"], f"V2 Master ({sample_id})", v2_raw_text, gt_text, v2_metrics["cer"], v2_metrics["wer"])

        cv2.imwrite(str(VIS_DIR / f"{sample_id}_v1.jpg"), v1_vis)
        cv2.imwrite(str(VIS_DIR / f"{sample_id}_v2.jpg"), v2_vis)

        # Side-by-side comparison image
        max_h = max(v1_vis.shape[0], v2_vis.shape[0])
        max_w = max(v1_vis.shape[1], v2_vis.shape[1])
        side_by_side = np.zeros((max_h, max_w * 2, 3), dtype=np.uint8)
        side_by_side[:v1_vis.shape[0], :v1_vis.shape[1]] = v1_vis
        side_by_side[:v2_vis.shape[0], max_w:max_w + v2_vis.shape[1]] = v2_vis
        cv2.imwrite(str(VIS_DIR / f"{sample_id}_comparison_side_by_side.jpg"), side_by_side)

    # Save structured breakdown JSON
    out_json = REPORTS / "physical_regression_investigation.json"
    out_json.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
    print(f"\nVisualizations saved to: {VIS_DIR}")
    print(f"Structured investigation report saved to: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
