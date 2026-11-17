#!/usr/bin/env python3
"""Validate Sciobraille user contribution ZIPs into a private quarantine.

This script never modifies master_v2 and never treats predicted boxes as ground
truth. A human must review consent, privacy, transcript, and box annotations
before promoting a sample into a versioned training dataset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


SCHEMA_VERSION = 1
MAX_ARCHIVE_BYTES = 60 * 1024 * 1024
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
ALLOWED_ENTRIES = {"image.jpg", "metadata.json", "README.txt"}
MANIFEST_FIELDS = [
    "contribution_id",
    "imported_at_utc",
    "source_package",
    "image_sha256",
    "raw_model_text",
    "user_corrected_text",
    "detection_count",
    "consent_version",
    "review_status",
]


class ContributionError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_existing_hashes(manifest: Path) -> set[str]:
    if not manifest.exists():
        return set()
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        return {row.get("image_sha256", "") for row in csv.DictReader(handle)}


def validate_id(value: Any) -> str:
    text = str(value or "")
    try:
        return str(uuid.UUID(text))
    except ValueError as exc:
        raise ContributionError("invalid contribution_id") from exc


def validate_metadata(metadata: dict[str, Any], image_data: bytes) -> None:
    if metadata.get("schema_version") != SCHEMA_VERSION:
        raise ContributionError(f"unsupported schema_version: {metadata.get('schema_version')!r}")
    validate_id(metadata.get("contribution_id"))
    if metadata.get("image_file") != "image.jpg":
        raise ContributionError("image_file must be image.jpg")
    if metadata.get("image_sha256") != sha256(image_data):
        raise ContributionError("image SHA256 does not match metadata")
    if not str(metadata.get("user_corrected_text", "")).strip():
        raise ContributionError("user_corrected_text is empty")
    consent = metadata.get("consent")
    if not isinstance(consent, dict):
        raise ContributionError("consent record is missing")
    for key in ("affirmative", "adult_or_authorized_representative", "no_sensitive_content_confirmed"):
        if consent.get(key) is not True:
            raise ContributionError(f"consent.{key} must be true")
    uses = set(consent.get("approved_uses") or [])
    required_uses = {"manual_annotation", "model_training", "model_evaluation"}
    if not required_uses.issubset(uses):
        raise ContributionError("approved uses do not include annotation, training, and evaluation")

    boxes = metadata.get("predicted_boxes")
    if not isinstance(boxes, list):
        raise ContributionError("predicted_boxes must be a list")
    for index, box in enumerate(boxes):
        if not isinstance(box, dict):
            raise ContributionError(f"box {index} is not an object")
        label = box.get("label")
        class_id = box.get("class_id")
        if not isinstance(label, str) or len(label) != 1 or not ("a" <= label.lower() <= "z"):
            raise ContributionError(f"box {index} has invalid label")
        if class_id != ord(label.lower()) - ord("a"):
            raise ContributionError(f"box {index} class_id does not match label")
        try:
            x1, y1, x2, y2 = (float(box[key]) for key in ("x1", "y1", "x2", "y2"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ContributionError(f"box {index} has invalid coordinates") from exc
        if not (0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0):
            raise ContributionError(f"box {index} coordinates are outside normalized bounds")


def read_package(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ContributionError("input is not a ZIP file")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ContributionError("archive exceeds size limit")
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ContributionError("invalid ZIP archive") from exc
    with archive:
        names = set(archive.namelist())
        if not {"image.jpg", "metadata.json"}.issubset(names):
            raise ContributionError("archive is missing image.jpg or metadata.json")
        if names - ALLOWED_ENTRIES:
            raise ContributionError(f"archive contains unexpected entries: {sorted(names - ALLOWED_ENTRIES)}")
        image_info = archive.getinfo("image.jpg")
        metadata_info = archive.getinfo("metadata.json")
        if image_info.file_size > MAX_IMAGE_BYTES or metadata_info.file_size > MAX_METADATA_BYTES:
            raise ContributionError("archive entry exceeds size limit")
        image_data = archive.read(image_info)
        try:
            metadata = json.loads(archive.read(metadata_info).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContributionError("metadata.json is invalid") from exc

    if not isinstance(metadata, dict):
        raise ContributionError("metadata root must be an object")
    try:
        with Image.open(io.BytesIO(image_data)) as image:
            image.verify()
        with Image.open(io.BytesIO(image_data)) as image:
            width, height = image.size
            if image.format != "JPEG" or width < 64 or height < 64:
                raise ContributionError("image must be a valid JPEG of at least 64 by 64 pixels")
    except ContributionError:
        raise
    except Exception as exc:
        raise ContributionError("image.jpg is corrupt or unsupported") from exc
    validate_metadata(metadata, image_data)
    return metadata, image_data


def append_manifest(manifest: Path, row: dict[str, Any]) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    exists = manifest.exists() and manifest.stat().st_size > 0
    with manifest.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in MANIFEST_FIELDS})


def import_package(
    package: Path,
    quarantine: Path,
    manifest: Path,
    known_hashes: set[str],
    dry_run: bool,
) -> str:
    metadata, image_data = read_package(package)
    image_hash = sha256(image_data)
    contribution_id = validate_id(metadata["contribution_id"])
    if image_hash in known_hashes:
        raise ContributionError("duplicate image SHA256")
    destination = quarantine / contribution_id
    if destination.exists():
        raise ContributionError("contribution_id already exists")
    if dry_run:
        return contribution_id

    destination.mkdir(parents=True)
    try:
        (destination / "image.jpg").write_bytes(image_data)
        shutil.copy2(package, destination / "original-package.zip")
        (destination / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        (destination / "review.json").write_text(
            json.dumps(
                {
                    "status": "needs_privacy_and_annotation_review",
                    "approved_for_training": False,
                    "reviewer": "",
                    "reviewed_at_utc": "",
                    "notes": "Predicted boxes are not ground truth.",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        append_manifest(
            manifest,
            {
                "contribution_id": contribution_id,
                "imported_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_package": package.name,
                "image_sha256": image_hash,
                "raw_model_text": metadata.get("raw_model_text", ""),
                "user_corrected_text": metadata.get("user_corrected_text", ""),
                "detection_count": metadata.get("detection_count", 0),
                "consent_version": metadata.get("consent", {}).get("version", ""),
                "review_status": "needs_privacy_and_annotation_review",
            },
        )
        known_hashes.add(image_hash)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return contribution_id


def find_packages(inputs: list[Path]) -> list[Path]:
    packages: set[Path] = set()
    for value in inputs:
        if value.is_dir():
            packages.update(value.glob("*.zip"))
        else:
            packages.add(value)
    return sorted(path.resolve() for path in packages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Contribution ZIP files or directories")
    parser.add_argument(
        "--quarantine",
        type=Path,
        default=Path("sciobraille-model-lab/datasets/user_contributions/quarantine"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("sciobraille-model-lab/datasets/user_contributions/contributions_manifest.csv"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    packages = find_packages(args.inputs)
    if not packages:
        print("No contribution ZIP files found.", file=sys.stderr)
        return 2
    known_hashes = load_existing_hashes(args.manifest)
    failures = 0
    for package in packages:
        try:
            contribution_id = import_package(
                package, args.quarantine, args.manifest, known_hashes, args.dry_run
            )
            print(f"OK {package}: {contribution_id}")
        except ContributionError as exc:
            failures += 1
            print(f"REJECTED {package}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
