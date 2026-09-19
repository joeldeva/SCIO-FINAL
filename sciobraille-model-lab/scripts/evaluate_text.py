#!/usr/bin/env python3
"""Text metrics for Sciobraille benchmarks.

Accuracy inputs must be raw OCR text, not corrected/demo text.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lower()
    text = re.sub(r"[^\w\s\n]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def levenshtein(left: list[str] | str, right: list[str] | str) -> int:
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, lc in enumerate(left, 1):
        current = [i]
        for j, rc in enumerate(right, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (0 if lc == rc else 1)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def text_metrics(ground_truth: str, prediction: str) -> dict[str, float | int | bool]:
    truth = normalize_text(ground_truth)
    pred = normalize_text(prediction)
    truth_chars = list(truth)
    pred_chars = list(pred)
    truth_words = truth.split()
    pred_words = pred.split()
    char_distance = levenshtein(truth_chars, pred_chars)
    word_distance = levenshtein(truth_words, pred_words)
    char_total = max(1, len(truth_chars))
    word_total = max(1, len(truth_words))
    cer = char_distance / char_total
    wer = word_distance / word_total
    return {
        "char_distance": char_distance,
        "word_distance": word_distance,
        "truth_chars": len(truth_chars),
        "truth_words": len(truth_words),
        "cer": cer,
        "wer": wer,
        "character_accuracy": max(0.0, 1.0 - cer),
        "word_accuracy": max(0.0, 1.0 - wer),
        "exact_sentence_accuracy": truth == pred,
    }


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "sample_count": 0,
            "cer": None,
            "wer": None,
            "character_accuracy": None,
            "word_accuracy": None,
            "exact_sentence_accuracy": None,
        }
    return {
        "sample_count": len(rows),
        "cer": sum(float(r["cer"]) for r in rows) / len(rows),
        "wer": sum(float(r["wer"]) for r in rows) / len(rows),
        "character_accuracy": sum(float(r["character_accuracy"]) for r in rows) / len(rows),
        "word_accuracy": sum(float(r["word_accuracy"]) for r in rows) / len(rows),
        "exact_sentence_accuracy": sum(1 for r in rows if r["exact_sentence_accuracy"]) / len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    rows = []
    with args.predictions.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics = text_metrics(row["ground_truth"], row["raw_text"])
            rows.append({**row, **metrics})

    payload = {"aggregate": aggregate(rows), "samples": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["aggregate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
