#!/usr/bin/env python3
"""Baseline benchmark for existing Sciobraille production model.

Read-only. Does not train. Does not overwrite production model.
Text accuracy uses raw_text only.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import cv2

from evaluate_text import aggregate, text_metrics


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
REPORTS = LAB / "reports"
DEFAULT_MODEL = ROOT / "sciobraille-scanner" / "backend" / "model" / "best.pt"
DEFAULT_DATA = ROOT / "prabh-decoders-braillevision" / "dataset" / "braille_merged" / "data.yaml"
DEFAULT_GT = LAB / "benchmark" / "ground_truth.csv"


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def load_scanner(model_path: Path):
    backend = ROOT / "sciobraille-scanner" / "backend"
    sys.path.insert(0, str(backend))
    os.environ["MODEL_PATH"] = str(model_path)
    module = importlib.import_module("scanner_api")
    return module


def run_text_benchmark(scanner: Any, ground_truth_csv: Path, repeat: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    with ground_truth_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for item in reader:
            image_path = resolve_path(item["image_path"])
            image = cv2.imread(str(image_path))
            if image is None:
                rows.append(
                    {
                        **item,
                        "raw_text": "",
                        "corrected_text": "",
                        "detections": 0,
                        "confidence": 0.0,
                        "error": "image_load_failed",
                    }
                )
                continue
            flip = item.get("flip_horizontal", "").strip().lower()
            flip_value = None if flip == "" else flip in {"1", "true", "yes", "on"}
            result = None
            sample_latencies = []
            for _ in range(max(1, repeat)):
                scanner.history.clear()
                start = time.perf_counter()
                result = scanner._predict(image, include_image=False, flip_horizontal=flip_value)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                sample_latencies.append(elapsed_ms)
                latencies.append(elapsed_ms)
            assert result is not None
            raw_text = result.get("raw_text", "")
            corrected_text = result.get("text", "")
            metrics = text_metrics(item["ground_truth"], raw_text)
            rows.append(
                {
                    **item,
                    "raw_text": raw_text,
                    "corrected_text": corrected_text,
                    "detections": result.get("detections", 0),
                    "confidence": result.get("confidence", 0.0),
                    "latency_ms_avg_sample": sum(sample_latencies) / len(sample_latencies),
                    "latency_ms_median_sample": statistics.median(sample_latencies),
                    "error": "",
                    **metrics,
                }
            )
    valid_rows = [row for row in rows if not row.get("error")]
    summary = aggregate(valid_rows)
    summary["average_inference_latency_ms"] = sum(latencies) / len(latencies) if latencies else None
    summary["median_inference_latency_ms"] = statistics.median(latencies) if latencies else None
    return rows, summary


def run_detection_validation(model_path: Path, data_yaml: Path, imgsz: int, conf: float) -> dict[str, Any]:
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    start = time.perf_counter()
    result = model.val(
        data=str(data_yaml),
        imgsz=imgsz,
        conf=conf,
        split="val",
        verbose=False,
        project=str(REPORTS / "ultralytics"),
        name="v1_original_val",
        exist_ok=True,
        plots=False,
    )
    elapsed = time.perf_counter() - start
    box = result.box
    return {
        "data_yaml": str(data_yaml),
        "split": "val",
        "precision": float(box.mp),
        "recall": float(box.mr),
        "mAP50": float(box.map50),
        "mAP50_95": float(box.map),
        "validation_seconds": elapsed,
        "note": "Detection metrics use YOLO validation data, not independent physical text benchmark.",
    }


def write_predictions_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "image_path",
        "benchmark_type",
        "flip_horizontal",
        "ground_truth",
        "raw_text",
        "corrected_text",
        "detections",
        "confidence",
        "latency_ms_avg_sample",
        "latency_ms_median_sample",
        "cer",
        "wer",
        "character_accuracy",
        "word_accuracy",
        "exact_sentence_accuracy",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    text = payload["text_metrics"]
    det = payload.get("detection_metrics")
    lines = [
        "# Sciobraille V1 Original Baseline",
        "",
        "Read-only baseline. No training. Production model not modified.",
        "",
        "## Model",
        "",
        f"- path: `{payload['model']['path']}`",
        f"- size bytes: `{payload['model']['size_bytes']}`",
        f"- size MB: `{payload['model']['size_mb']}`",
        "",
        "## Detection Metrics",
        "",
    ]
    if det:
        lines.extend(
            [
                f"- data: `{det['data_yaml']}`",
                f"- split: `{det['split']}`",
                f"- precision: `{det['precision']}`",
                f"- recall: `{det['recall']}`",
                f"- mAP50: `{det['mAP50']}`",
                f"- mAP50-95: `{det['mAP50_95']}`",
                f"- note: {det['note']}",
            ]
        )
    else:
        lines.append("- Not available. Validation failed or skipped.")
    lines.extend(
        [
            "",
            "## Text Metrics",
            "",
            "Text accuracy uses `raw_text` only. `corrected_text` saved for comparison, not scoring.",
            "",
            f"- samples: `{text['sample_count']}`",
            f"- Character Error Rate: `{text['cer']}`",
            f"- Word Error Rate: `{text['wer']}`",
            f"- character accuracy: `{text['character_accuracy']}`",
            f"- word accuracy: `{text['word_accuracy']}`",
            f"- exact sentence accuracy: `{text['exact_sentence_accuracy']}`",
            f"- average inference latency ms: `{text['average_inference_latency_ms']}`",
            f"- median inference latency ms: `{text['median_inference_latency_ms']}`",
            "",
            "## Benchmark Caveat",
            "",
            payload["benchmark_caveat"],
            "",
            "## Files",
            "",
            "- predictions: `reports/v1_original_predictions.csv`",
            "- JSON: `reports/v1_original_baseline.json`",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--skip-detection", action="store_true")
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    scanner = load_scanner(args.model)
    rows, text_summary = run_text_benchmark(scanner, args.ground_truth, args.repeat)
    detection = None
    detection_error = None
    if not args.skip_detection:
        try:
            detection = run_detection_validation(args.model, args.data, args.imgsz, args.conf)
        except Exception as exc:
            detection_error = f"{type(exc).__name__}: {exc}"
    model_size = args.model.stat().st_size
    payload = {
        "model": {
            "path": str(args.model),
            "size_bytes": model_size,
            "size_mb": round(model_size / (1024 * 1024), 4),
        },
        "detection_metrics": detection,
        "detection_error": detection_error,
        "text_metrics": text_summary,
        "samples": rows,
        "benchmark_caveat": (
            "Independent physical benchmark is still too small. Add 50-100 held-out phone-camera physical Braille images "
            "with exact human ground truth before using text metrics as release gate."
        ),
    }
    write_predictions_csv(REPORTS / "v1_original_predictions.csv", rows)
    (REPORTS / "v1_original_baseline.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(REPORTS / "v1_original_baseline.md", payload)
    print(json.dumps({"text_metrics": text_summary, "detection_metrics": detection, "detection_error": detection_error}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
