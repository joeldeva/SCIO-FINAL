#!/usr/bin/env python3
"""Evaluate new user-supplied physical Braille photographs on V1 and V2 models.

Supports:
- Ground-truth transcription verification (strictly raw_text, no spelling correction)
- Metadata grouping (document_id, capture_group_id, orientation, lighting, blur, distance, perspective)
- Comparative side-by-side metrics: raw CER, raw WER, character accuracy, word accuracy, latency
- Automatic validation of field manifest against independent_physical_schema.py
- Zero fabrication: reports exact stats when images are provided, or explains schema requirements if empty
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
SCRIPTS = LAB / "scripts"
BENCHMARK = LAB / "benchmark"
REPORTS = LAB / "reports"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(BENCHMARK))

import independent_physical_schema
import tune_inference
from evaluate_text import aggregate, text_metrics

DEFAULT_V1 = ROOT / "sciobraille-scanner" / "backend" / "model" / "best.pt"
DEFAULT_V2 = LAB / "models" / "v2_master" / "best.pt"
DEFAULT_CONFIG = LAB / "configs" / "v1_optimized.yaml"


def evaluate_model_on_records(
    model: YOLO,
    records: list[independent_physical_schema.PhysicalBenchmarkRecord],
    config: tune_inference.Config,
) -> list[dict[str, Any]]:
    results = []
    for rec in records:
        img = cv2.imread(str(rec.image_path))
        if img is None:
            results.append({
                "id": rec.id,
                "error": f"Failed to load image at {rec.image_path}",
                "raw_text": "",
                "cer": 1.0,
                "wer": 1.0,
            })
            continue

        # In physical field evaluation, meta_flip depends on orientation:
        meta_flip = (rec.orientation == "reverse")
        t0 = time.perf_counter()
        infer_res = tune_inference.infer(model, model.names, img, config, meta_flip)
        latency = (time.perf_counter() - t0) * 1000.0

        raw_pred = infer_res["raw_text"]
        metrics = text_metrics(rec.ground_truth_transcription, raw_pred)

        results.append({
            "id": rec.id,
            "document_id": rec.document_id,
            "capture_group_id": rec.capture_group_id,
            "orientation": rec.orientation,
            "lighting": rec.lighting,
            "blur": rec.blur,
            "distance": rec.distance,
            "perspective": rec.perspective,
            "line_count": rec.line_count,
            "ground_truth": rec.ground_truth_transcription,
            "raw_text": raw_pred,
            "detections_count": infer_res["detections"],
            "latency_ms": round(latency, 2),
            "cer": metrics["cer"],
            "wer": metrics["wer"],
            "char_accuracy": metrics["character_accuracy"],
            "word_accuracy": metrics["word_accuracy"],
            "exact_sentence_match": metrics["exact_sentence_accuracy"],
            "notes": rec.notes,
        })
    return results


def generate_field_report(
    output_dir: Path,
    manifest_path: Path,
    v1_results: list[dict[str, Any]],
    v2_results: list[dict[str, Any]],
    v1_path: Path,
    v2_path: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "field_evaluation_report.md"
    csv_file = output_dir / "field_evaluation_comparison.csv"

    # Write CSV comparison
    comparison_rows = []
    for r1, r2 in zip(v1_results, v2_results):
        comparison_rows.append({
            "id": r1["id"],
            "document_id": r1["document_id"],
            "orientation": r1["orientation"],
            "lighting": r1["lighting"],
            "blur": r1["blur"],
            "distance": r1["distance"],
            "perspective": r1["perspective"],
            "ground_truth": r1["ground_truth"].replace("\n", " / "),
            "v1_raw_text": r1["raw_text"].replace("\n", " / "),
            "v2_raw_text": r2["raw_text"].replace("\n", " / "),
            "v1_cer": r1["cer"],
            "v2_cer": r2["cer"],
            "v1_wer": r1["wer"],
            "v2_wer": r2["wer"],
            "v1_detections": r1.get("detections_count", 0),
            "v2_detections": r2.get("detections_count", 0),
            "v1_latency_ms": r1["latency_ms"],
            "v2_latency_ms": r2["latency_ms"],
        })

    fieldnames = list(comparison_rows[0].keys()) if comparison_rows else []
    if fieldnames:
        with csv_file.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comparison_rows)

    # Compute aggregates
    v1_agg = aggregate(v1_results) if v1_results else {}
    v2_agg = aggregate(v2_results) if v2_results else {}

    lines = [
        "# Sciobraille Independent Field Evaluation Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"- **Manifest:** `{manifest_path}`",
        f"- **Sample Count:** {len(v1_results)}",
        f"- **V1 Model:** `{v1_path}`",
        f"- **V2 Model:** `{v2_path}`",
        "",
        "## Summary Aggregate Metrics",
        "",
        "| Metric | Production V1 | Master V2 | Delta (V2 - V1) |",
        "|---|---:|---:|---:|",
        f"| **Raw CER** | {v1_agg.get('cer', 1.0):.4f} | {v2_agg.get('cer', 1.0):.4f} | {v2_agg.get('cer', 1.0) - v1_agg.get('cer', 1.0):+.4f} |",
        f"| **Raw WER** | {v1_agg.get('wer', 1.0):.4f} | {v2_agg.get('wer', 1.0):.4f} | {v2_agg.get('wer', 1.0) - v1_agg.get('wer', 1.0):+.4f} |",
        f"| **Character Accuracy** | {v1_agg.get('character_accuracy', 0.0):.4f} | {v2_agg.get('character_accuracy', 0.0):.4f} | {v2_agg.get('character_accuracy', 0.0) - v1_agg.get('character_accuracy', 0.0):+.4f} |",
        f"| **Word Accuracy** | {v1_agg.get('word_accuracy', 0.0):.4f} | {v2_agg.get('word_accuracy', 0.0):.4f} | {v2_agg.get('word_accuracy', 0.0) - v1_agg.get('word_accuracy', 0.0):+.4f} |",
        f"| **Exact Match** | {v1_agg.get('exact_sentence_accuracy', 0.0):.4f} | {v2_agg.get('exact_sentence_accuracy', 0.0):.4f} | {v2_agg.get('exact_sentence_accuracy', 0.0) - v1_agg.get('exact_sentence_accuracy', 0.0):+.4f} |",
        "",
        "## Per-Sample Breakdown",
        "",
        "| Sample ID | Document | Cond (Light/Blur/Dist/Persp) | Ground Truth | V1 Raw Output | V2 Raw Output | V1 CER | V2 CER |",
        "|---|---|---|---|---|---|---:|---:|",
    ]
    for row in comparison_rows:
        cond = f"{row['lighting']}/{row['blur']}/{row['distance']}/{row['perspective']}"
        lines.append(
            f"| `{row['id']}` | `{row['document_id']}` | {cond} | `{row['ground_truth'][:30]}` | `{row['v1_raw_text'][:30]}` | `{row['v2_raw_text'][:30]}` | {row['v1_cer']:.4f} | {row['v2_cer']:.4f} |"
        )

    lines.extend([
        "",
        "## Detailed Data Export",
        f"- CSV Comparison: `{csv_file.name}`",
        "",
        "> [!IMPORTANT]",
        "> Accuracy calculations use raw model outputs only. No spell checker, language model, or dictionary substitution is applied.",
    ])

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate user-supplied physical Braille photos on V1 and V2")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to CSV manifest following independent_physical_schema.py")
    parser.add_argument("--output-dir", type=Path, default=REPORTS / "field_evaluation", help="Directory for output report and CSV")
    parser.add_argument("--v1-model", type=Path, default=DEFAULT_V1)
    parser.add_argument("--v2-model", type=Path, default=DEFAULT_V2)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        print(f"Error: Manifest file not found at {manifest_path}", file=sys.stderr)
        return 1

    records = independent_physical_schema.load_independent_benchmark(manifest_path)
    if not records:
        print(f"Manifest '{manifest_path}' contains 0 valid physical evaluation records.")
        print("Please populate the CSV manifest with physical Braille image records.")
        print(f"Template schema available at: {BENCHMARK / 'independent_physical_template.csv'}")
        return 0

    print(f"Loaded {len(records)} physical evaluation records from {manifest_path}")

    # Validate records
    has_errors = False
    for r in records:
        errs = r.validate()
        if errs:
            has_errors = True
            print(f"Validation error in record '{r.id}': {', '.join(errs)}", file=sys.stderr)
    if has_errors:
        print("Aborting: manifest validation failed.", file=sys.stderr)
        return 1

    cfg_data = yaml.safe_load(args.config.resolve().read_text(encoding="utf-8"))["configuration"]
    config = tune_inference.Config(**cfg_data)

    print(f"Loading V1: {args.v1_model}")
    v1_model = YOLO(str(args.v1_model))
    print(f"Loading V2: {args.v2_model}")
    v2_model = YOLO(str(args.v2_model))

    print(f"Evaluating V1 on {len(records)} field samples...")
    v1_res = evaluate_model_on_records(v1_model, records, config)
    print(f"Evaluating V2 on {len(records)} field samples...")
    v2_res = evaluate_model_on_records(v2_model, records, config)

    report_path = generate_field_report(args.output_dir.resolve(), manifest_path, v1_res, v2_res, args.v1_model, args.v2_model)
    print(f"Field evaluation complete. Report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
