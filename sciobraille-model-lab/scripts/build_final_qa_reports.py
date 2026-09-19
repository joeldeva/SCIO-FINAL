#!/usr/bin/env python3
"""Build final end-to-end and online/offline comparison reports from frozen runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
BACKEND_PATH = REPORTS / "final_e2e_backend.json"
OFFLINE_PATH = REPORTS / "final_e2e_offline.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_text(value: str) -> str:
    return value.replace("\r\n", "\n")


def write_online_offline(backend: dict, offline: dict) -> None:
    offline_by_id = {sample["id"]: sample for sample in offline["samples"]}
    target = REPORTS / "online_offline_comparison.csv"
    fields = [
        "image", "ground_truth", "backend_raw", "offline_raw", "backend_CER",
        "offline_CER", "backend_latency", "offline_latency",
    ]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for online in backend["samples"]:
            local = offline_by_id[online["id"]]
            writer.writerow({
                "image": online["image_path"],
                "ground_truth": format_text(online["ground_truth"]),
                "backend_raw": format_text(online["raw_text"]),
                "offline_raw": format_text(local["raw_text"]),
                "backend_CER": online["cer"],
                "offline_CER": local["cer"],
                "backend_latency": online["latency_ms_median"],
                "offline_latency": local["latency_ms_median"],
            })


def write_benchmark_csv(backend: dict, offline: dict) -> None:
    target = REPORTS / "final_end_to_end_benchmark.csv"
    fields = [
        "runtime", "image", "ground_truth", "raw_text", "detections", "confidence",
        "CER", "WER", "character_accuracy", "word_accuracy", "exact_match",
        "average_latency_ms", "median_latency_ms", "error",
    ]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for runtime, report in (("backend_pt", backend), ("android_int8", offline)):
            for sample in report["samples"]:
                writer.writerow({
                    "runtime": runtime,
                    "image": sample["image_path"],
                    "ground_truth": format_text(sample["ground_truth"]),
                    "raw_text": format_text(sample["raw_text"]),
                    "detections": sample["detections"],
                    "confidence": sample["confidence"],
                    "CER": sample["cer"],
                    "WER": sample["wer"],
                    "character_accuracy": sample["character_accuracy"],
                    "word_accuracy": sample["word_accuracy"],
                    "exact_match": sample["exact_sentence_accuracy"],
                    "average_latency_ms": sample["latency_ms_average"],
                    "median_latency_ms": sample["latency_ms_median"],
                    "error": sample["error"],
                })


def metric_row(label: str, report: dict) -> str:
    summary = report["summary"]
    return (
        f"| {label} | {summary['cer']:.4f} | {summary['wer']:.4f} | "
        f"{summary['character_accuracy']:.4f} | {summary['word_accuracy']:.4f} | "
        f"{summary['exact_sentence_accuracy']:.4f} | {summary['average_latency_ms']:.2f} ms | "
        f"{summary['median_latency_ms']:.2f} ms |"
    )


def write_markdown(backend: dict, offline: dict) -> None:
    lines = [
        "# Final End-to-End Braille Benchmark",
        "",
        "Accuracy source: `raw_text` only. Corrected text did not affect any metric.",
        "",
        "The frozen benchmark contains three physical phone-camera samples. Results are regression evidence, not a production accuracy claim.",
        "",
        "| Runtime | CER | WER | Character accuracy | Word accuracy | Exact match | Average latency | Median latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric_row("Backend PT", backend),
        metric_row("Android INT8 artifact", offline),
        "",
        "## Failure Breakdown",
        "",
    ]
    offline_by_id = {sample["id"]: sample for sample in offline["samples"]}
    for sample in backend["samples"]:
        local = offline_by_id[sample["id"]]
        lines.extend([
            f"### {sample['id']}",
            "",
            f"- Backend raw CER/WER: {sample['cer']:.4f} / {sample['wer']:.4f}",
            f"- Offline raw CER/WER: {local['cer']:.4f} / {local['wer']:.4f}",
            f"- Backend detections: {sample['detections']}",
            f"- Offline detections: {local['detections']}",
            f"- Backend raw: `{sample['raw_text'].replace(chr(10), ' / ') or '<empty>'}`",
            f"- Offline raw: `{local['raw_text'].replace(chr(10), ' / ') or '<empty>'}`",
            "",
        ])
    lines.extend([
        "## Observed Failures",
        "",
        "- Both runtimes fail on the unflipped DMI sample when default reverse-side flipping is applied.",
        "- Backend PT has character substitutions and one extra cell on the Sciobraille sample.",
        "- Android INT8 is more accurate on these three samples, but Windows TFLite latency is not representative of phone latency.",
        "- Exact sentence match is zero for both runtimes.",
        "- Lighting, blur, distance, perspective, and spacing categories cannot be measured independently because the frozen set lacks enough labeled samples.",
        "",
        "## Required Benchmark Expansion",
        "",
        "Add 50-100 independent physical samples with exact ground truth and category labels for normal/dim/harsh light, shadows, blur, perspective, close/long range, reverse-side Braille, multiple lines, and word spacing.",
        "",
    ])
    (REPORTS / "final_end_to_end_benchmark.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    backend = load(BACKEND_PATH)
    offline = load(OFFLINE_PATH)
    write_online_offline(backend, offline)
    write_benchmark_csv(backend, offline)
    write_markdown(backend, offline)


if __name__ == "__main__":
    main()
