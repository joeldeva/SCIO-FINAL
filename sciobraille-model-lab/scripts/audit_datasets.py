#!/usr/bin/env python3
"""Audit Sciobraille/BrailleVision datasets, labels, models, and scripts.

Read-only audit. Does not merge datasets, train models, or modify production code.
Writes reports under sciobraille-model-lab/reports.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
REPORTS = LAB / "reports"

PROJECTS = [
    "sciobraille-scanner",
    "prabh-decoders-braillevision",
    "sangam-Braillie",
    "asmitha",
    "braille_hackathon_siddhant",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MODEL_EXTS = {".pt", ".onnx", ".tflite", ".pb"}
TRAIN_RE = re.compile(r"(train|training|fit|yolo).*\.py$", re.IGNORECASE)
INFER_RE = re.compile(r"(infer|predict|detect|scanner|api|app|main).*\.py$", re.IGNORECASE)
BENCHMARK_HINTS = (
    "sample",
    "judge",
    "test",
    "benchmark",
    "output",
    "demo",
    "eval",
    "evaluate",
)


@dataclass
class DatasetAudit:
    source: str
    yaml_path: Path | None
    root: Path
    classes: dict[int, str]
    splits: dict[str, dict[str, Path | None]] = field(default_factory=dict)
    image_count: int = 0
    label_count: int = 0
    annotation_count: int = 0
    bbox_count: int = 0
    split_image_counts: Counter = field(default_factory=Counter)
    split_label_counts: Counter = field(default_factory=Counter)
    split_annotation_counts: Counter = field(default_factory=Counter)
    split_bbox_counts: Counter = field(default_factory=Counter)
    class_counts: Counter = field(default_factory=Counter)
    class_ids_seen: set[int] = field(default_factory=set)
    dimensions: Counter = field(default_factory=Counter)
    sha256: dict[str, str] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Small YAML reader for data.yaml shapes used here."""
    data: dict[str, Any] = {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                child = lines[j].split("#", 1)[0].rstrip()
                if not child.strip():
                    j += 1
                    continue
                if child.startswith("- "):
                    items.append(child[2:].strip().strip("'\""))
                    j += 1
                    continue
                if child.startswith("  - "):
                    items.append(child[4:].strip().strip("'\""))
                    j += 1
                    continue
                break
            if items:
                data[key] = items
                i = j
                continue
            data[key] = ""
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                data[key] = [x.strip().strip("'\"") for x in inner.split(",")]
            else:
                data[key] = []
        else:
            data[key] = value.strip("'\"")
        i += 1
    return data


def class_map(yaml_data: dict[str, Any]) -> dict[int, str]:
    names = yaml_data.get("names", [])
    if isinstance(names, list):
        return {i: str(name) for i, name in enumerate(names)}
    if isinstance(names, dict):
        return {int(k): str(v) for k, v in names.items()}
    return {}


def resolve_dataset_path(yaml_path: Path, yaml_data: dict[str, Any], value: Any) -> Path | None:
    if value is None or value == "":
        return None
    path = Path(str(value))
    base = Path(str(yaml_data.get("path", ""))) if yaml_data.get("path") else yaml_path.parent
    if path.is_absolute():
        return path
    if base.is_absolute():
        return base / path
    return (yaml_path.parent / base / path).resolve()


def split_image_dir(yaml_path: Path, yaml_data: dict[str, Any], split_key: str, split_name: str) -> Path | None:
    configured = resolve_dataset_path(yaml_path, yaml_data, yaml_data.get(split_key))
    if configured and configured.exists():
        return configured
    candidates = [
        yaml_path.parent / split_name / "images",
        yaml_path.parent / ("valid" if split_name == "val" else split_name) / "images",
        yaml_path.parent / "images" / split_name,
        yaml_path.parent / "images" / ("valid" if split_name == "val" else split_name),
        yaml_path.parent.parent / split_name / "images",
        yaml_path.parent.parent / ("valid" if split_name == "val" else split_name) / "images",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return configured


def infer_label_dir(image_dir: Path | None) -> Path | None:
    if image_dir is None:
        return None
    parts = list(image_dir.parts)
    for idx, part in enumerate(parts):
        if part == "images":
            parts[idx] = "labels"
            return Path(*parts)
    if image_dir.name == "images":
        return image_dir.parent / "labels"
    return image_dir.parent.parent / "labels" / image_dir.name


def find_images(path: Path | None) -> list[Path]:
    if path is None or not path.exists():
        return []
    if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def find_labels(path: Path | None) -> list[Path]:
    if path is None or not path.exists():
        return []
    if path.is_file() and path.suffix.lower() == ".txt":
        return [path]
    return sorted(p for p in path.rglob("*.txt") if p.is_file())


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            return img.size
    except Exception:
        try:
            import cv2

            img = cv2.imread(str(path))
            if img is None:
                return None
            h, w = img.shape[:2]
            return w, h
        except Exception:
            return None


def label_for_image(image: Path, image_dir: Path, label_dir: Path | None) -> Path | None:
    if label_dir is None:
        return None
    try:
        rel_image = image.relative_to(image_dir)
    except ValueError:
        rel_image = Path(image.name)
    return (label_dir / rel_image).with_suffix(".txt")


def image_for_label(label: Path, label_dir: Path, image_dir: Path | None) -> Path | None:
    if image_dir is None:
        return None
    try:
        rel_label = label.relative_to(label_dir)
    except ValueError:
        rel_label = Path(label.name)
    stem = (image_dir / rel_label).with_suffix("")
    for ext in IMAGE_EXTS:
        candidate = Path(str(stem) + ext)
        if candidate.exists():
            return candidate
    return Path(str(stem) + ".jpg")


def audit_label(
    audit: DatasetAudit,
    split: str,
    label: Path,
    valid_classes: set[int],
) -> int:
    boxes = 0
    text = label.read_text(encoding="utf-8", errors="replace").splitlines()
    for line_no, line in enumerate(text, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        audit.annotation_count += 1
        audit.split_annotation_counts[split] += 1
        parts = stripped.split()
        if len(parts) != 5:
            audit.errors.append(
                {
                    "source": audit.source,
                    "split": split,
                    "type": "invalid_label_columns",
                    "path": rel(label),
                    "detail": f"line {line_no}: expected 5 columns got {len(parts)}",
                }
            )
            continue
        try:
            class_id = int(float(parts[0]))
            coords = [float(x) for x in parts[1:]]
        except ValueError:
            audit.errors.append(
                {
                    "source": audit.source,
                    "split": split,
                    "type": "invalid_label_number",
                    "path": rel(label),
                    "detail": f"line {line_no}: non-numeric YOLO row",
                }
            )
            continue
        audit.class_ids_seen.add(class_id)
        audit.class_counts[class_id] += 1
        audit.split_bbox_counts[split] += 1
        boxes += 1
        if valid_classes and class_id not in valid_classes:
            audit.errors.append(
                {
                    "source": audit.source,
                    "split": split,
                    "type": "invalid_class_id",
                    "path": rel(label),
                    "detail": f"line {line_no}: class {class_id}",
                }
            )
        if any(v < 0 or v > 1 for v in coords):
            audit.errors.append(
                {
                    "source": audit.source,
                    "split": split,
                    "type": "invalid_yolo_coordinates",
                    "path": rel(label),
                    "detail": f"line {line_no}: {coords}",
                }
            )
    return boxes


def audit_dataset(source: str, yaml_path: Path) -> DatasetAudit:
    data = parse_simple_yaml(yaml_path)
    classes = class_map(data)
    root = resolve_dataset_path(yaml_path, data, ".") or yaml_path.parent
    audit = DatasetAudit(source=source, yaml_path=yaml_path, root=root, classes=classes)
    valid_classes = set(classes)
    for split_key, split_name in [("train", "train"), ("val", "val"), ("valid", "val"), ("test", "test")]:
        if split_key not in data:
            continue
        image_dir = split_image_dir(yaml_path, data, split_key, split_name)
        label_dir = infer_label_dir(image_dir)
        audit.splits[split_name] = {"images": image_dir, "labels": label_dir}
        if image_dir is None or not image_dir.exists():
            audit.errors.append(
                {
                    "source": source,
                    "split": split_name,
                    "type": "missing_split_images_dir",
                    "path": rel(yaml_path),
                    "detail": str(data.get(split_key, "")),
                }
            )
        if label_dir is None or not label_dir.exists():
            audit.errors.append(
                {
                    "source": source,
                    "split": split_name,
                    "type": "missing_split_labels_dir",
                    "path": rel(yaml_path),
                    "detail": rel(label_dir),
                }
            )
        images = find_images(image_dir)
        labels = find_labels(label_dir)
        audit.split_image_counts[split_name] += len(images)
        audit.split_label_counts[split_name] += len(labels)
        audit.image_count += len(images)
        audit.label_count += len(labels)
        for image in images:
            audit.sha256[rel(image)] = sha256_file(image)
            dims = image_dimensions(image)
            if dims is None:
                audit.errors.append(
                    {
                        "source": source,
                        "split": split_name,
                        "type": "corrupt_image",
                        "path": rel(image),
                        "detail": "image decoder failed",
                    }
                )
            else:
                audit.dimensions[dims] += 1
            label = label_for_image(image, image_dir or image.parent, label_dir)
            if label is None or not label.exists():
                audit.errors.append(
                    {
                        "source": source,
                        "split": split_name,
                        "type": "missing_label",
                        "path": rel(image),
                        "detail": rel(label),
                    }
                )
        for label in labels:
            image = image_for_label(label, label_dir or label.parent, image_dir)
            if image is None or not image.exists():
                audit.errors.append(
                    {
                        "source": source,
                        "split": split_name,
                        "type": "missing_image",
                        "path": rel(label),
                        "detail": rel(image),
                    }
                )
            audit.bbox_count += audit_label(audit, split_name, label, valid_classes)
    return audit


def project_name(path: Path) -> str:
    try:
        first = path.relative_to(ROOT).parts[0]
        return first
    except Exception:
        return ""


def discover_data_yamls() -> list[Path]:
    paths = []
    for project in PROJECTS:
        base = ROOT / project
        if base.exists():
            paths.extend(base.rglob("data.yaml"))
    return sorted(set(paths))


def discover_files() -> dict[str, list[Path]]:
    files = {"models": [], "training_scripts": [], "inference_scripts": [], "benchmark_assets": []}
    for project in PROJECTS:
        base = ROOT / project
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            name = path.name
            rel_lower = rel(path).lower()
            if suffix in MODEL_EXTS:
                files["models"].append(path)
            if suffix == ".py" and TRAIN_RE.search(name):
                files["training_scripts"].append(path)
            if suffix == ".py" and INFER_RE.search(name):
                files["inference_scripts"].append(path)
            if suffix in IMAGE_EXTS | {".mp4", ".json", ".csv", ".txt"} and any(h in rel_lower for h in BENCHMARK_HINTS):
                if "dataset/" not in rel_lower and "\\dataset\\" not in rel_lower:
                    files["benchmark_assets"].append(path)
    return {k: sorted(v) for k, v in files.items()}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(audits: list[DatasetAudit], discovered: dict[str, list[Path]]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    inventory_rows: list[dict[str, Any]] = []
    class_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for audit in audits:
        inventory_rows.append(
            {
                "source_dataset": audit.source,
                "data_yaml": rel(audit.yaml_path),
                "dataset_root": rel(audit.root),
                "image_count": audit.image_count,
                "label_count": audit.label_count,
                "annotation_row_count": audit.annotation_count,
                "bounding_box_count": audit.bbox_count,
                "train_images": audit.split_image_counts["train"],
                "val_images": audit.split_image_counts["val"],
                "test_images": audit.split_image_counts["test"],
                "train_labels": audit.split_label_counts["train"],
                "val_labels": audit.split_label_counts["val"],
                "test_labels": audit.split_label_counts["test"],
                "train_annotations": audit.split_annotation_counts["train"],
                "val_annotations": audit.split_annotation_counts["val"],
                "test_annotations": audit.split_annotation_counts["test"],
                "train_boxes": audit.split_bbox_counts["train"],
                "val_boxes": audit.split_bbox_counts["val"],
                "test_boxes": audit.split_bbox_counts["test"],
                "class_count": len(audit.classes),
                "class_ids_seen": " ".join(map(str, sorted(audit.class_ids_seen))),
                "classes": json.dumps(audit.classes, ensure_ascii=False),
                "top_dimensions": json.dumps(
                    {f"{w}x{h}": c for (w, h), c in audit.dimensions.most_common(10)},
                    ensure_ascii=False,
                ),
                "sha256_manifest_count": len(audit.sha256),
                "error_count": len(audit.errors),
            }
        )
        for class_id in sorted(set(audit.classes) | set(audit.class_counts)):
            class_rows.append(
                {
                    "source_dataset": audit.source,
                    "class_id": class_id,
                    "class_name": audit.classes.get(class_id, ""),
                    "box_count": audit.class_counts[class_id],
                }
            )
        error_rows.extend(audit.errors)

        sha_path = REPORTS / f"sha256_{audit.source}.csv"
        write_csv(
            sha_path,
            [{"path": p, "sha256": h} for p, h in sorted(audit.sha256.items())],
            ["path", "sha256"],
        )

    write_csv(REPORTS / "dataset_inventory.csv", inventory_rows, list(inventory_rows[0]) if inventory_rows else [])
    write_csv(REPORTS / "class_distribution.csv", class_rows, ["source_dataset", "class_id", "class_name", "box_count"])
    write_csv(REPORTS / "dataset_errors.csv", error_rows, ["source", "split", "type", "path", "detail"])

    lines: list[str] = []
    lines.append("# Sciobraille Dataset Audit\n")
    lines.append("Read-only audit. No merge. No training. No production model changes.\n")
    lines.append("## Datasets Found\n")
    for audit in audits:
        lines.append(f"### {audit.source}\n")
        lines.append(f"- data.yaml: `{rel(audit.yaml_path)}`")
        lines.append(f"- root: `{rel(audit.root)}`")
        lines.append(f"- images: {audit.image_count}")
        lines.append(f"- labels: {audit.label_count}")
        lines.append(f"- annotation rows: {audit.annotation_count}")
        lines.append(f"- valid 5-column bounding boxes: {audit.bbox_count}")
        lines.append(
            f"- split images: train={audit.split_image_counts['train']}, "
            f"val={audit.split_image_counts['val']}, test={audit.split_image_counts['test']}"
        )
        lines.append(
            f"- split labels: train={audit.split_label_counts['train']}, "
            f"val={audit.split_label_counts['val']}, test={audit.split_label_counts['test']}"
        )
        lines.append(
            f"- split annotations: train={audit.split_annotation_counts['train']}, "
            f"val={audit.split_annotation_counts['val']}, test={audit.split_annotation_counts['test']}"
        )
        lines.append(
            f"- split boxes: train={audit.split_bbox_counts['train']}, "
            f"val={audit.split_bbox_counts['val']}, test={audit.split_bbox_counts['test']}"
        )
        lines.append(f"- classes: `{json.dumps(audit.classes, ensure_ascii=False)}`")
        lines.append(f"- class IDs seen: `{sorted(audit.class_ids_seen)}`")
        lines.append(
            "- top dimensions: "
            + ", ".join(f"{w}x{h}={c}" for (w, h), c in audit.dimensions.most_common(8))
        )
        lines.append(f"- SHA256 image rows: {len(audit.sha256)}")
        lines.append(f"- errors: {len(audit.errors)}\n")

    lines.append("## Models Found\n")
    for path in discovered["models"]:
        lines.append(f"- `{rel(path)}` ({path.stat().st_size} bytes)")
    lines.append("\n## Training Scripts Found\n")
    for path in discovered["training_scripts"]:
        lines.append(f"- `{rel(path)}`")
    lines.append("\n## Inference Scripts Found\n")
    for path in discovered["inference_scripts"]:
        lines.append(f"- `{rel(path)}`")
    lines.append("\n## Benchmark / Evaluation Assets Found\n")
    for path in discovered["benchmark_assets"][:500]:
        lines.append(f"- `{rel(path)}`")
    if len(discovered["benchmark_assets"]) > 500:
        lines.append(f"- ... truncated in markdown, total={len(discovered['benchmark_assets'])}")

    lines.append("\n## Model To Dataset Mapping, Evidence-Based\n")
    lines.append("- `sciobraille-scanner/backend/model/best.pt`: documented as Prabh Model B, trained from `prabh-decoders-braillevision/dataset/braille_merged`.")
    lines.append("- `sciobraille-scanner/backend/model/best_previous_A.pt`: duplicate lineage of Prabh Model A.")
    lines.append("- `prabh-decoders-braillevision/model/best.pt`: documented Model A/large benchmark from Prabh project.")
    lines.append("- `prabh-decoders-braillevision/model/best_B.pt`: same active production model lineage.")
    lines.append("- `sangam-Braillie/model/best.pt`: Sangam 26-class model, expected to use `sangam-Braillie/dataset`.")
    lines.append("- `sangam-Braillie/model/yolov8_braille.pt`: 64-class dot-pattern model; dataset linkage needs manual validation.")
    lines.append("- `asmitha/runs/detect/*/weights/*.pt`: Asmitha training runs, expected to use `asmitha/dataset`.")
    lines.append("- `braille_hackathon_siddhant/model/best.pt`: Siddhant reference model; included dataset appears incomplete locally.")

    lines.append("\n## Problems Discovered\n")
    if error_rows:
        by_type = Counter(row["type"] for row in error_rows)
        for err_type, count in by_type.most_common():
            lines.append(f"- {err_type}: {count}")
    else:
        lines.append("- No dataset errors found by automated checks.")
    lines.append("\nDetailed rows: `dataset_errors.csv`.\n")
    (REPORTS / "dataset_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    yaml_paths = discover_data_yamls()
    audits = []
    for yaml_path in yaml_paths:
        source = rel(yaml_path.parent).replace("/", "__").replace("\\", "__")
        audits.append(audit_dataset(source, yaml_path))
    discovered = discover_files()
    write_reports(audits, discovered)
    print(f"audited_datasets={len(audits)}")
    print(f"reports={rel(REPORTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
