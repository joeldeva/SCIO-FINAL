#!/usr/bin/env python3
"""Benchmark one Sciobraille model export using raw recognition text only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import statistics
import sys
import time
from pathlib import Path

import cv2

from evaluate_text import aggregate, text_metrics


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "sciobraille-scanner" / "backend"
DEFAULT_GT = ROOT / "sciobraille-model-lab" / "benchmark" / "ground_truth.csv"


def resolve_image(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def load_scanner(
    model_path: Path,
    confidence: float,
    iou: float,
    enhance: bool,
    augment: bool,
    default_flip: bool,
):
    os.environ["MODEL_PATH"] = str(model_path.resolve())
    os.environ["BRAILLE_CONF"] = str(confidence)
    os.environ["BRAILLE_IOU"] = str(iou)
    os.environ["BRAILLE_IMGSZ"] = "640"
    os.environ["BRAILLE_ENHANCE"] = str(enhance).lower()
    os.environ["BRAILLE_AUGMENT"] = str(augment).lower()
    os.environ["BRAILLE_FLIP_HORIZONTAL"] = str(default_flip).lower()
    sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("scanner_api_export_benchmark", BACKEND / "scanner_api.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load scanner backend")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--confidence", type=float, default=0.50)
    parser.add_argument("--iou", type=float, default=0.50)
    parser.add_argument("--enhance", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--augment", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--default-flip", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    scanner = load_scanner(
        args.model,
        args.confidence,
        args.iou,
        args.enhance,
        args.augment,
        args.default_flip,
    )
    rows = []
    all_latencies = []
    with args.ground_truth.open("r", encoding="utf-8", newline="") as stream:
        for item in csv.DictReader(stream):
            frame = cv2.imread(str(resolve_image(item["image_path"])))
            if frame is None:
                rows.append({**item, "error": "image_load_failed"})
                continue
            flip_raw = item.get("flip_horizontal", "").strip().lower()
            flip = None if not flip_raw else flip_raw in {"1", "true", "yes", "on"}
            sample_latencies = []
            result = None
            for _ in range(max(1, args.repeat)):
                start = time.perf_counter()
                result = scanner._predict(frame, include_image=False, flip_horizontal=flip)
                sample_latencies.append((time.perf_counter() - start) * 1000.0)
            assert result is not None
            all_latencies.extend(sample_latencies)
            raw_text = result.get("raw_text", "")
            metrics = text_metrics(item["ground_truth"], raw_text)
            rows.append(
                {
                    **item,
                    "raw_text": raw_text,
                    "corrected_text": result.get("corrected_text", result.get("text", "")),
                    "detections": result.get("detections", 0),
                    "confidence": result.get("confidence", 0.0),
                    "latency_ms_average": sum(sample_latencies) / len(sample_latencies),
                    "latency_ms_median": statistics.median(sample_latencies),
                    "error": "",
                    **metrics,
                }
            )

    valid = [row for row in rows if not row.get("error")]
    summary = aggregate(valid)
    summary.update(
        {
            "average_latency_ms": sum(all_latencies) / len(all_latencies) if all_latencies else None,
            "median_latency_ms": statistics.median(all_latencies) if all_latencies else None,
        }
    )
    payload = {
        "name": args.name,
        "model": str(args.model.resolve()),
        "sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
        "size_bytes": args.model.stat().st_size,
        "accuracy_source": "raw_text",
        "configuration": {
            "confidence": args.confidence,
            "iou": args.iou,
            "imgsz": 640,
            "enhance": args.enhance,
            "augment": args.augment,
            "default_flip_horizontal": args.default_flip,
        },
        "summary": summary,
        "samples": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    predictions = args.output.with_suffix(".csv")
    fields = list(rows[0]) if rows else ["id", "error"]
    with predictions.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
