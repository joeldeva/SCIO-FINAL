#!/usr/bin/env python3
"""Validate source or built Master V2 YOLO labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from master_dataset_common import MASTER, REPORTS, Candidate, CANONICAL, discover_candidates, inspect_all, write_csv


def master_candidates(root: Path) -> list[Candidate]:
    candidates = []
    for split in ("train", "val", "test"):
        image_dir, label_dir = root / "images" / split, root / "labels" / split
        if not image_dir.exists():
            continue
        image_paths = sorted(path for path in image_dir.iterdir() if path.is_file())
        image_stems = {path.stem for path in image_paths}
        for image_path in image_paths:
            candidates.append(Candidate("master_v2", root, image_path, label_dir / f"{image_path.stem}.txt", split, CANONICAL))
        if label_dir.exists():
            for label_path in sorted(label_dir.glob("*.txt")):
                if label_path.stem in image_stems:
                    continue
                candidates.append(
                    Candidate("master_v2", root, image_dir / f"{label_path.stem}.jpg", label_path, split, CANONICAL)
                )
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, help="Validate built master root instead of sources")
    parser.add_argument("--output", type=Path, default=REPORTS / "master_v2_label_qa.csv")
    args = parser.parse_args()
    candidates = master_candidates(args.master.resolve()) if args.master else discover_candidates()[0]
    inspect_all(candidates)
    rows = [record for candidate in candidates for record in [*candidate.errors, *candidate.warnings]]
    write_csv(args.output, rows, ["source_dataset", "image_path", "label_path", "split", "issue_type", "line_number", "detail", "severity"])
    summary = {
        "images": len(candidates),
        "usable_images": sum(candidate.valid for candidate in candidates),
        "boxes": sum(len(candidate.boxes) for candidate in candidates if candidate.valid),
        "errors": sum(len(candidate.errors) for candidate in candidates),
        "warnings": sum(len(candidate.warnings) for candidate in candidates),
        "converted_polygons": sum(candidate.converted_polygons for candidate in candidates),
    }
    print(json.dumps(summary, indent=2))
    if args.master and summary["errors"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
