#!/usr/bin/env python3
"""Shared deterministic utilities for Sciobraille Master Dataset V2."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
REPORTS = LAB / "reports"
MASTER = LAB / "datasets" / "master_v2"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CANONICAL = {index: chr(ord("a") + index) for index in range(26)}
NAME_TO_CANONICAL = {name: index for index, name in CANONICAL.items()}


@dataclass(frozen=True)
class Source:
    name: str
    root: Path
    data_yaml: Path
    splits: dict[str, tuple[Path, Path]]


@dataclass
class Box:
    class_id: int
    x: float
    y: float
    width: float
    height: float
    source_format: str = "box"

    def line(self) -> str:
        return f"{self.class_id} {self.x:.8f} {self.y:.8f} {self.width:.8f} {self.height:.8f}"


@dataclass
class Candidate:
    source: str
    source_root: Path
    image_path: Path
    label_path: Path
    original_split: str
    mapping: dict[int, str]
    sha256: str = ""
    phash: str = ""
    dhash: str = ""
    width: int = 0
    height: int = 0
    capture_key: str = ""
    boxes: list[Box] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    converted_polygons: int = 0
    visual_signature: np.ndarray | None = field(default=None, repr=False)
    edge_signature: np.ndarray | None = field(default=None, repr=False)

    @property
    def valid(self) -> bool:
        return self.width > 0 and self.height > 0 and bool(self.boxes) and not self.errors


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def source_definitions() -> list[Source]:
    prabh = ROOT / "prabh-decoders-braillevision" / "dataset" / "braille_merged"
    asmitha = ROOT / "asmitha" / "dataset"
    sangam = ROOT / "sangam-Braillie" / "dataset"
    return [
        Source(
            "prabh_braille_merged",
            prabh,
            prabh / "data.yaml",
            {
                "train": (prabh / "images" / "train", prabh / "labels" / "train"),
                "val": (prabh / "images" / "val", prabh / "labels" / "val"),
            },
        ),
        Source(
            "sangam_braillie",
            sangam,
            sangam / "data.yaml",
            {
                "train": (sangam / "train" / "images", sangam / "train" / "labels"),
                "val": (sangam / "valid" / "images", sangam / "valid" / "labels"),
                "test": (sangam / "test" / "images", sangam / "test" / "labels"),
            },
        ),
        Source(
            "asmitha",
            asmitha,
            asmitha / "data.yaml",
            {
                "train": (asmitha / "train" / "images", asmitha / "train" / "labels"),
                "val": (asmitha / "valid" / "images", asmitha / "valid" / "labels"),
                "test": (asmitha / "test" / "images", asmitha / "test" / "labels"),
            },
        ),
    ]


def load_mapping(data_yaml: Path) -> dict[int, str]:
    data = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    names = data.get("names", {})
    if isinstance(names, list):
        return {index: str(name) for index, name in enumerate(names)}
    return {int(index): str(name) for index, name in names.items()}


def canonical_mapping(mapping: dict[int, str]) -> tuple[dict[int, int], list[tuple[int, str]]]:
    remap: dict[int, int] = {}
    unsupported = []
    for source_id, source_name in mapping.items():
        normalized = source_name.strip().lower()
        if normalized in NAME_TO_CANONICAL:
            remap[source_id] = NAME_TO_CANONICAL[normalized]
        else:
            unsupported.append((source_id, source_name))
    return remap, unsupported


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bit_hash(image: np.ndarray, kind: str) -> str:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if kind == "dhash":
        resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        bits = resized[:, 1:] > resized[:, :-1]
    elif kind == "phash":
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
        low = cv2.dct(resized)[:8, :8]
        values = low.flatten()
        median = np.median(values[1:])
        bits = low > median
    else:
        raise ValueError(kind)
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def normalized_visual_signature(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (48, 48), interpolation=cv2.INTER_AREA).astype(np.float32)
    mean, standard_deviation = float(resized.mean()), float(resized.std())
    if standard_deviation < 1e-6:
        return np.zeros_like(resized)
    return (resized - mean) / standard_deviation


def visual_edge_signature(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (96, 96), interpolation=cv2.INTER_AREA)
    normalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(resized)
    edges = cv2.Canny(normalized, 35, 100)
    edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)
    return edges > 0


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def capture_key(path: Path) -> str:
    stem = path.stem.lower()
    stem = stem.split(".rf.", 1)[0]
    stem = re.sub(r"_(jpg|jpeg|png)$", "", stem)
    stem = re.sub(r"[-_](aug|copy|flip|flipped|rotated|rotate|bright|dark|noise|blur)\d*$", "", stem)
    return stem


def issue(candidate: Candidate, issue_type: str, detail: str, line_number: int | None = None, severity: str = "error") -> None:
    record = {
        "source_dataset": candidate.source,
        "image_path": str(candidate.image_path),
        "label_path": str(candidate.label_path),
        "split": candidate.original_split,
        "issue_type": issue_type,
        "line_number": line_number if line_number is not None else "",
        "detail": detail,
        "severity": severity,
    }
    (candidate.errors if severity == "error" else candidate.warnings).append(record)


def parse_label(candidate: Candidate) -> None:
    remap, unsupported_mapping = canonical_mapping(candidate.mapping)
    for source_id, source_name in unsupported_mapping:
        issue(candidate, "unsupported_class_mapping", f"source class {source_id}={source_name}")
    if not candidate.label_path.exists():
        issue(candidate, "missing_label", "image has no matching label file")
        return
    try:
        lines = candidate.label_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        issue(candidate, "unreadable_label", str(exc))
        return
    if not lines:
        issue(candidate, "empty_label", "label file contains no annotations")
        return

    seen: set[tuple[int, float, float, float, float]] = set()
    for line_number, raw in enumerate(lines, 1):
        tokens = raw.strip().split()
        if not tokens:
            continue
        try:
            class_value = float(tokens[0])
            if not class_value.is_integer():
                raise ValueError("class ID is not integer")
            source_class = int(class_value)
            values = [float(value) for value in tokens[1:]]
        except ValueError as exc:
            issue(candidate, "invalid_label_value", str(exc), line_number)
            continue
        if source_class not in candidate.mapping:
            issue(candidate, "invalid_class_id", f"class ID {source_class} absent from source mapping", line_number)
            continue
        if source_class not in remap:
            source_name = candidate.mapping[source_class]
            issue(candidate, "unsupported_class", f"class ID {source_class}={source_name}", line_number)
            continue
        if not all(math.isfinite(value) for value in values):
            issue(candidate, "non_finite_coordinate", raw, line_number)
            continue

        source_format = "box"
        if len(values) == 4:
            x, y, width, height = values
        elif len(values) >= 6 and len(values) % 2 == 0:
            xs, ys = values[0::2], values[1::2]
            if any(value < 0.0 or value > 1.0 for value in values):
                issue(candidate, "polygon_coordinate_outside_range", raw, line_number)
                continue
            x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
            x, y, width, height = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
            source_format = "polygon_converted"
            candidate.converted_polygons += 1
        else:
            issue(candidate, "invalid_label_columns", f"found {len(tokens)} columns", line_number)
            continue

        if any(value < 0.0 or value > 1.0 for value in (x, y, width, height)):
            issue(candidate, "coordinate_outside_yolo_range", raw, line_number)
            continue
        if width <= 0.0 or height <= 0.0:
            issue(candidate, "zero_width_or_height", raw, line_number)
            continue
        canonical_id = remap[source_class]
        key = (canonical_id, round(x, 7), round(y, 7), round(width, 7), round(height, 7))
        if key in seen:
            issue(candidate, "duplicate_box", raw, line_number, severity="warning")
            continue
        seen.add(key)
        candidate.boxes.append(Box(canonical_id, x, y, width, height, source_format))

    for left_index, left in enumerate(candidate.boxes):
        for right in candidate.boxes[left_index + 1 :]:
            overlap = box_iou(left, right)
            if overlap >= 0.90 and left.class_id != right.class_id:
                issue(
                    candidate,
                    "suspicious_overlap_different_class",
                    f"IoU={overlap:.5f}; classes={left.class_id},{right.class_id}",
                    severity="warning",
                )
            elif overlap >= 0.98:
                issue(candidate, "suspicious_overlap_same_class", f"IoU={overlap:.5f}; class={left.class_id}", severity="warning")
    if not candidate.boxes and not candidate.errors:
        issue(candidate, "no_usable_boxes", "no valid annotations remain")


def box_iou(left: Box, right: Box) -> float:
    left_x1, left_y1 = left.x - left.width / 2, left.y - left.height / 2
    left_x2, left_y2 = left.x + left.width / 2, left.y + left.height / 2
    right_x1, right_y1 = right.x - right.width / 2, right.y - right.height / 2
    right_x2, right_y2 = right.x + right.width / 2, right.y + right.height / 2
    intersection = max(0.0, min(left_x2, right_x2) - max(left_x1, right_x1)) * max(
        0.0, min(left_y2, right_y2) - max(left_y1, right_y1)
    )
    union = left.width * left.height + right.width * right.height - intersection
    return intersection / union if union else 0.0


def discover_candidates() -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    discovery = []
    configured_yamls = {source.data_yaml.resolve() for source in source_definitions()}
    for source in source_definitions():
        mapping = load_mapping(source.data_yaml)
        count = 0
        for split, (image_dir, label_dir) in source.splits.items():
            if not image_dir.exists():
                discovery.append({"data_yaml": str(source.data_yaml), "status": "missing_split", "detail": str(image_dir)})
                continue
            image_paths = sorted(path for path in image_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
            image_stems = {path.relative_to(image_dir).with_suffix("") for path in image_paths}
            for image_path in image_paths:
                relative = image_path.relative_to(image_dir).with_suffix(".txt")
                candidates.append(Candidate(source.name, source.root, image_path, label_dir / relative, split, mapping))
                count += 1
            if label_dir.exists():
                for label_path in sorted(label_dir.rglob("*.txt")):
                    relative_stem = label_path.relative_to(label_dir).with_suffix("")
                    if relative_stem in image_stems:
                        continue
                    candidate = Candidate(
                        source.name,
                        source.root,
                        image_dir / relative_stem.with_suffix(".jpg"),
                        label_path,
                        split,
                        mapping,
                    )
                    issue(candidate, "missing_image", "label has no matching image")
                    candidates.append(candidate)
        discovery.append({"data_yaml": str(source.data_yaml), "status": "included", "detail": f"{count} candidate images"})

    for data_yaml in ROOT.rglob("data.yaml"):
        if data_yaml.resolve() in configured_yamls or LAB in data_yaml.parents:
            continue
        try:
            mapping = load_mapping(data_yaml)
            _, unsupported = canonical_mapping(mapping)
            image_count = sum(1 for path in data_yaml.parent.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
            label_count = sum(1 for path in data_yaml.parent.rglob("*.txt") if "labels" in path.parts)
            status = "not_usable"
            reason = f"images={image_count}, labels={label_count}, unsupported_mapping={len(unsupported)}"
            discovery.append({"data_yaml": str(data_yaml), "status": status, "detail": reason})
        except Exception as exc:
            discovery.append({"data_yaml": str(data_yaml), "status": "inspection_error", "detail": str(exc)})
    return candidates, discovery


def inspect_candidate(candidate: Candidate) -> None:
    if not candidate.image_path.exists():
        if not any(record["issue_type"] == "missing_image" for record in candidate.errors):
            issue(candidate, "missing_image", "image file does not exist")
        return
    try:
        file_bytes = np.fromfile(candidate.image_path, dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except (OSError, cv2.error) as exc:
        issue(candidate, "corrupt_image", str(exc))
        return
    if image is None or image.size == 0:
        issue(candidate, "corrupt_image", "OpenCV could not decode image")
        return
    candidate.height, candidate.width = image.shape[:2]
    candidate.sha256 = file_sha256(candidate.image_path)
    candidate.phash = bit_hash(image, "phash")
    candidate.dhash = bit_hash(image, "dhash")
    candidate.visual_signature = normalized_visual_signature(image)
    candidate.edge_signature = visual_edge_signature(image)
    candidate.capture_key = capture_key(candidate.image_path)
    parse_label(candidate)


def inspect_all(candidates: list[Candidate]) -> None:
    for index, candidate in enumerate(candidates, 1):
        inspect_candidate(candidate)
        if index % 250 == 0 or index == len(candidates):
            print(f"Inspected {index}/{len(candidates)}", flush=True)


def duplicate_groups(candidates: list[Candidate]) -> tuple[list[list[int]], dict[str, int]]:
    valid_indexes = [index for index, candidate in enumerate(candidates) if candidate.valid]
    union = UnionFind(len(candidates))
    exact_links = 0
    capture_links = 0
    near_links = 0

    by_sha: dict[str, list[int]] = {}
    by_capture: dict[tuple[str, str], list[int]] = {}
    for index in valid_indexes:
        candidate = candidates[index]
        by_sha.setdefault(candidate.sha256, []).append(index)
        by_capture.setdefault((candidate.source, candidate.capture_key), []).append(index)
    for group in by_sha.values():
        for index in group[1:]:
            union.union(group[0], index)
            exact_links += 1
    for group in by_capture.values():
        if len(group) < 2:
            continue
        for index in group[1:]:
            union.union(group[0], index)
            capture_links += 1

    for position, left_index in enumerate(valid_indexes):
        left = candidates[left_index]
        left_ratio = left.width / left.height
        left_classes = tuple(sorted(box.class_id for box in left.boxes))
        for right_index in valid_indexes[position + 1 :]:
            right = candidates[right_index]
            if left_classes != tuple(sorted(box.class_id for box in right.boxes)):
                continue
            right_ratio = right.width / right.height
            if abs(left_ratio - right_ratio) / max(left_ratio, right_ratio) > 0.02:
                continue
            p_distance = hamming(left.phash, right.phash)
            if p_distance > 3:
                continue
            d_distance = hamming(left.dhash, right.dhash)
            if d_distance > 3:
                continue
            assert left.visual_signature is not None and right.visual_signature is not None
            correlation = float(np.mean(left.visual_signature * right.visual_signature))
            if correlation < 0.985:
                continue
            assert left.edge_signature is not None and right.edge_signature is not None
            intersection = int(np.logical_and(left.edge_signature, right.edge_signature).sum())
            union_pixels = int(np.logical_or(left.edge_signature, right.edge_signature).sum())
            edge_overlap = intersection / union_pixels if union_pixels else 0.0
            if edge_overlap >= 0.72:
                if union.find(left_index) != union.find(right_index):
                    union.union(left_index, right_index)
                    near_links += 1

    grouped: dict[int, list[int]] = {}
    for index in valid_indexes:
        grouped.setdefault(union.find(index), []).append(index)
    groups = sorted(grouped.values(), key=lambda group: min(candidates[index].sha256 for index in group))
    return groups, {"exact_links": exact_links, "capture_links": capture_links, "near_links": near_links}


def candidate_quality(candidate: Candidate) -> tuple[int, int, int, int, str]:
    source_priority = {"prabh_braille_merged": 3, "sangam_braillie": 2, "asmitha": 1}
    return (
        len(candidate.boxes),
        -len(candidate.warnings),
        candidate.width * candidate.height,
        source_priority.get(candidate.source, 0),
        candidate.sha256,
    )


def group_id(candidates: list[Candidate], group: list[int]) -> str:
    digest = hashlib.sha256("|".join(sorted(candidates[index].sha256 for index in group)).encode("ascii")).hexdigest()
    return "group_" + digest[:16]


def external_benchmark_hashes() -> set[str]:
    hashes = set()
    benchmark_csv = LAB / "benchmark" / "ground_truth.csv"
    if not benchmark_csv.exists():
        return hashes
    import csv

    with benchmark_csv.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            image_path = Path(row["image_path"])
            if not image_path.is_absolute():
                image_path = ROOT / image_path
            if image_path.exists():
                hashes.add(file_sha256(image_path))
    return hashes


def deterministic_split(group_identifier: str) -> str:
    value = int(hashlib.sha256(("SciobrailleV2:" + group_identifier).encode("utf-8")).hexdigest()[:8], 16) % 10000
    if value < 8000:
        return "train"
    if value < 9000:
        return "val"
    return "test"


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def mapping_json(mapping: dict[int, str]) -> str:
    return json.dumps({str(index): name for index, name in sorted(mapping.items())}, sort_keys=True)
