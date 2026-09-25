#!/usr/bin/env python3
"""Evaluation schema and validator for independent physical Braille benchmarks.

Separates real-world independent evaluation from model selection, hyperparameter
tuning, and training.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_FIELDNAMES = [
    "id",
    "image_path",
    "ground_truth_transcription",
    "document_id",
    "capture_group_id",
    "orientation",           # 'front' or 'reverse'
    "lighting",              # 'ambient', 'direct', 'shadow', 'low_light', etc.
    "blur",                  # 'sharp', 'mild_motion', 'severe_blur', etc.
    "distance",              # 'close', 'medium', 'far'
    "perspective",           # 'planar', 'slight_tilt', 'steep_angle', etc.
    "line_count",            # integer >= 1
    "notes",
]


@dataclass
class PhysicalBenchmarkRecord:
    id: str
    image_path: Path
    ground_truth_transcription: str
    document_id: str
    capture_group_id: str
    orientation: str
    lighting: str
    blur: str
    distance: str
    perspective: str
    line_count: int
    notes: str = ""

    def validate(self) -> list[str]:
        errors = []
        if not self.id:
            errors.append("Empty id")
        if not self.ground_truth_transcription:
            errors.append("Empty ground_truth_transcription")
        if self.orientation not in ("front", "reverse"):
            errors.append(f"Invalid orientation '{self.orientation}'; must be 'front' or 'reverse'")
        if self.line_count < 1:
            errors.append(f"Invalid line_count {self.line_count}; must be >= 1")
        if not self.image_path.exists():
            errors.append(f"Image file does not exist: {self.image_path}")
        return errors


def load_independent_benchmark(csv_path: Path) -> list[PhysicalBenchmarkRecord]:
    """Load and validate records from an independent benchmark CSV."""
    if not csv_path.exists():
        return []
    records = []
    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            sample_id = (row.get("id") or "").strip()
            if not sample_id or sample_id.startswith("#"):
                continue
            raw_path = (row.get("image_path") or "").strip()
            if not raw_path:
                continue
            record = PhysicalBenchmarkRecord(
                id=sample_id,
                image_path=Path(raw_path),
                ground_truth_transcription=row.get("ground_truth_transcription", ""),
                document_id=(row.get("document_id") or "").strip(),
                capture_group_id=(row.get("capture_group_id") or "").strip(),
                orientation=(row.get("orientation") or "front").strip().lower(),
                lighting=(row.get("lighting") or "").strip().lower(),
                blur=(row.get("blur") or "").strip().lower(),
                distance=(row.get("distance") or "").strip().lower(),
                perspective=(row.get("perspective") or "").strip().lower(),
                line_count=int(row["line_count"].strip()) if (row.get("line_count") or "").strip().isdigit() else 0,
                notes=(row.get("notes") or "").strip(),
            )
            records.append(record)
    return records
