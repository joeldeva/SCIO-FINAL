#!/usr/bin/env python3
"""Build unique, provenance-tracked Sciobraille Master Dataset V2."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from collections import Counter
from pathlib import Path

import yaml

from master_dataset_common import (
    CANONICAL,
    LAB,
    MASTER,
    REPORTS,
    candidate_quality,
    deterministic_split,
    discover_candidates,
    duplicate_groups,
    external_benchmark_hashes,
    group_id,
    inspect_all,
    mapping_json,
    write_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=MASTER)
    args = parser.parse_args()
    output = args.output.resolve()
    staging = output.with_name(output.name + "_building")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"Refusing to overwrite existing master dataset: {output}")
    if staging.exists():
        raise RuntimeError(f"Staging directory already exists: {staging}")

    candidates, discovery = discover_candidates()
    inspect_all(candidates)
    groups, link_counts = duplicate_groups(candidates)
    benchmark_hashes = external_benchmark_hashes()

    all_issues = [record for candidate in candidates for record in [*candidate.errors, *candidate.warnings]]
    unsupported = [
        record
        for record in all_issues
        if record["issue_type"] in {"unsupported_class", "unsupported_class_mapping", "invalid_class_id"}
    ]
    write_csv(
        REPORTS / "unsupported_classes.csv",
        unsupported,
        ["source_dataset", "image_path", "label_path", "split", "issue_type", "line_number", "detail", "severity"],
    )
    write_csv(
        REPORTS / "master_v2_label_qa.csv",
        all_issues,
        ["source_dataset", "image_path", "label_path", "split", "issue_type", "line_number", "detail", "severity"],
    )

    duplicate_rows = []
    retained = []
    excluded_benchmark_groups = 0
    exact_duplicate_images = 0
    near_duplicate_images = 0
    for group in groups:
        identifier = group_id(candidates, group)
        exact_unique = len({candidates[index].sha256 for index in group})
        exact_duplicate_images += len(group) - exact_unique
        if len(group) > exact_unique:
            near_duplicate_images += exact_unique - 1
        elif len(group) > 1:
            near_duplicate_images += len(group) - 1
        benchmark_overlap = any(candidates[index].sha256 in benchmark_hashes for index in group)
        if benchmark_overlap:
            excluded_benchmark_groups += 1
            representative_index = None
        else:
            representative_index = max(group, key=lambda index: candidate_quality(candidates[index]))
            retained.append((identifier, group, representative_index))
        for index in group:
            candidate = candidates[index]
            duplicate_rows.append(
                {
                    "group_id": identifier,
                    "group_size": len(group),
                    "retained": index == representative_index,
                    "excluded_external_benchmark": benchmark_overlap,
                    "source_dataset": candidate.source,
                    "original_path": str(candidate.image_path),
                    "sha256": candidate.sha256,
                    "perceptual_hash": candidate.phash,
                    "dhash": candidate.dhash,
                    "capture_key": candidate.capture_key,
                }
            )
    write_csv(
        REPORTS / "master_v2_duplicate_groups.csv",
        duplicate_rows,
        ["group_id", "group_size", "retained", "excluded_external_benchmark", "source_dataset", "original_path", "sha256", "perceptual_hash", "dhash", "capture_key"],
    )

    for split in ("train", "val", "test"):
        (staging / "images" / split).mkdir(parents=True, exist_ok=False)
        (staging / "labels" / split).mkdir(parents=True, exist_ok=False)

    provenance_rows = []
    class_distribution = Counter()
    split_counts = Counter()
    source_contribution = Counter()
    total_boxes = 0
    for identifier, group, representative_index in retained:
        candidate = candidates[representative_index]
        split = deterministic_split(identifier)
        master_id = "scio_v2_" + candidate.sha256[:16]
        extension = candidate.image_path.suffix.lower()
        destination_image = staging / "images" / split / f"{master_id}{extension}"
        destination_label = staging / "labels" / split / f"{master_id}.txt"
        shutil.copy2(candidate.image_path, destination_image)
        destination_label.write_text("\n".join(box.line() for box in candidate.boxes) + "\n", encoding="ascii")
        total_boxes += len(candidate.boxes)
        split_counts[split] += 1
        source_contribution[candidate.source] += 1
        class_distribution.update(box.class_id for box in candidate.boxes)
        provenance_rows.append(
            {
                "master_id": master_id,
                "master_split": split,
                "group_id": identifier,
                "group_size": len(group),
                "source_dataset": candidate.source,
                "original_path": str(candidate.image_path),
                "original_label_path": str(candidate.label_path),
                "original_split": candidate.original_split,
                "sha256": candidate.sha256,
                "perceptual_hash": candidate.phash,
                "dhash": candidate.dhash,
                "capture_key": candidate.capture_key,
                "width": candidate.width,
                "height": candidate.height,
                "bounding_boxes": len(candidate.boxes),
                "converted_polygon_rows": candidate.converted_polygons,
                "original_class_mapping": mapping_json(candidate.mapping),
                "duplicate_sources": json.dumps(sorted({candidates[index].source for index in group})),
                "duplicate_original_paths": json.dumps(sorted(str(candidates[index].image_path) for index in group)),
            }
        )

    write_csv(
        staging / "provenance.csv",
        provenance_rows,
        [
            "master_id", "master_split", "group_id", "group_size", "source_dataset", "original_path",
            "original_label_path", "original_split", "sha256", "perceptual_hash", "dhash", "capture_key", "width",
            "height", "bounding_boxes", "converted_polygon_rows", "original_class_mapping", "duplicate_sources",
            "duplicate_original_paths",
        ],
    )
    data_yaml = {
        "path": str(output).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 26,
        "names": [CANONICAL[index] for index in range(26)],
    }
    (staging / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8")

    invalid_images = sum(any(error["issue_type"] == "corrupt_image" for error in candidate.errors) for candidate in candidates)
    invalid_candidates = sum(not candidate.valid for candidate in candidates)
    candidate_boxes = sum(len(candidate.boxes) for candidate in candidates if candidate.valid)
    source_candidates = {}
    for source_name in sorted({candidate.source for candidate in candidates}):
        source_rows = [candidate for candidate in candidates if candidate.source == source_name]
        source_candidates[source_name] = {
            "images": len(source_rows),
            "usable_images": sum(candidate.valid for candidate in source_rows),
            "bounding_boxes": sum(len(candidate.boxes) for candidate in source_rows if candidate.valid),
            "split_counts": dict(Counter(candidate.original_split for candidate in source_rows)),
        }
    statistics = {
        "version": 2,
        "canonical_classes": {str(index): name for index, name in CANONICAL.items()},
        "candidate_images": len(candidates),
        "valid_candidates_before_deduplication": sum(candidate.valid for candidate in candidates),
        "invalid_candidates": invalid_candidates,
        "invalid_images": invalid_images,
        "candidate_bounding_boxes": candidate_boxes,
        "polygon_rows_converted_before_deduplication": sum(candidate.converted_polygons for candidate in candidates),
        "source_candidates": source_candidates,
        "usable_unique_images": len(retained),
        "total_bounding_boxes": total_boxes,
        "exact_duplicate_images_removed": exact_duplicate_images,
        "near_or_capture_duplicate_images_removed": near_duplicate_images,
        "duplicate_groups": len(groups),
        "external_benchmark_groups_excluded": excluded_benchmark_groups,
        "split_counts": dict(split_counts),
        "split_percentages": {split: count / len(retained) for split, count in split_counts.items()},
        "source_contribution": dict(source_contribution),
        "class_distribution": {CANONICAL[index]: class_distribution[index] for index in range(26)},
        "polygon_rows_converted_in_retained_images": sum(candidates[index].converted_polygons for _, _, index in retained),
        "deduplication_links": link_counts,
        "source_discovery": discovery,
        "deduplication_policy": {
            "exact": "SHA256 equality",
            "capture": "same normalized original filename within source",
            "near": "same class histogram; aspect ratio within 2%; pHash<=3; dHash<=3; pixel correlation>=0.985; edge overlap>=0.72",
            "retention": "one highest-quality representative per connected duplicate/capture group",
        },
        "split_policy": "deterministic group hash; 80% train, 10% val, 10% internal test",
        "external_benchmark_policy": "exact benchmark overlaps and their full duplicate group are excluded",
    }
    (staging / "dataset_statistics.json").write_text(json.dumps(statistics, indent=2), encoding="utf-8")
    readme = f"""# Sciobraille Master Dataset V2

Canonical 26-class English Grade 1 Braille-cell detection dataset.

## Counts

- candidate images: {len(candidates)}
- valid candidates before deduplication: {sum(candidate.valid for candidate in candidates)}
- candidate bounding boxes: {candidate_boxes}
- retained unique images: {len(retained)}
- bounding boxes: {total_boxes}
- train/val/test: {split_counts['train']}/{split_counts['val']}/{split_counts['test']}

## Construction

Sources: Prabh merged, Sangam Braillie, and Asmitha. No source file was changed or deleted.
Mappings were normalized to `0=a` through `25=z`. Valid polygon rows were explicitly converted to boxes.
Images with unsupported classes or invalid annotations were excluded and reported.
SHA256, perceptual hash, dHash, normalized capture names, and conservative near-duplicate matching formed leakage groups.
One representative was retained per group. External physical benchmark images remain separate.

See `provenance.csv`, `dataset_statistics.json`, and reports under `sciobraille-model-lab/reports/`.
"""
    (staging / "README.md").write_text(readme, encoding="utf-8")

    report_lines = [
        "# Master V2 Build Report", "",
        f"- candidate images: `{len(candidates)}`",
        f"- valid candidates before deduplication: `{sum(candidate.valid for candidate in candidates)}`",
        f"- invalid candidates: `{invalid_candidates}`",
        f"- invalid images: `{invalid_images}`",
        f"- candidate bounding boxes before deduplication: `{candidate_boxes}`",
        f"- polygon rows converted before deduplication: `{sum(candidate.converted_polygons for candidate in candidates)}`",
        f"- exact duplicate images removed: `{exact_duplicate_images}`",
        f"- near/capture duplicate images removed: `{near_duplicate_images}`",
        f"- usable unique images: `{len(retained)}`",
        f"- total bounding boxes: `{total_boxes}`",
        f"- split counts: `{dict(split_counts)}`",
        f"- source contribution: `{dict(source_contribution)}`",
        f"- unsupported class records: `{len(unsupported)}`",
        f"- external benchmark groups excluded: `{excluded_benchmark_groups}`",
        "", "## Class Distribution", "",
    ]
    report_lines.extend(f"- {CANONICAL[index]}: `{class_distribution[index]}`" for index in range(26))
    report_lines.extend(["", "## Source Candidates", ""])
    report_lines.extend(f"- {name}: `{details}`" for name, details in source_candidates.items())
    report_lines.extend(["", "## Additional Repository Inspection", ""])
    report_lines.extend(f"- `{item['data_yaml']}`: {item['status']} ({item['detail']})" for item in discovery)
    (REPORTS / "master_v2_build.md").write_text("\n".join(report_lines), encoding="utf-8")

    if output.exists():
        if any(output.iterdir()):
            raise RuntimeError(f"Output became non-empty during build: {output}")
        output.rmdir()
    os.replace(staging, output)
    print(json.dumps(statistics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
