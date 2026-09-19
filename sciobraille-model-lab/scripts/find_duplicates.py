#!/usr/bin/env python3
"""Find exact and perceptual duplicates across Sciobraille source datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from master_dataset_common import REPORTS, discover_candidates, duplicate_groups, group_id, inspect_all, write_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPORTS / "master_v2_duplicate_groups.csv")
    args = parser.parse_args()
    candidates, discovery = discover_candidates()
    inspect_all(candidates)
    groups, counts = duplicate_groups(candidates)
    rows = []
    for group in groups:
        identifier = group_id(candidates, group)
        for index in group:
            candidate = candidates[index]
            rows.append(
                {
                    "group_id": identifier,
                    "group_size": len(group),
                    "source_dataset": candidate.source,
                    "original_path": str(candidate.image_path),
                    "sha256": candidate.sha256,
                    "perceptual_hash": candidate.phash,
                    "dhash": candidate.dhash,
                    "capture_key": candidate.capture_key,
                }
            )
    write_csv(
        args.output,
        rows,
        ["group_id", "group_size", "source_dataset", "original_path", "sha256", "perceptual_hash", "dhash", "capture_key"],
    )
    print(json.dumps({"candidates": len(candidates), "valid": sum(candidate.valid for candidate in candidates), "groups": len(groups), **counts, "discovery": discovery}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
