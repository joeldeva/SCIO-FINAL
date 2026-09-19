#!/usr/bin/env python3
"""Staged inference tuning for Sciobraille V1.

Read-only with respect to production code and weights. No training.
All text metrics use raw reconstructed text. Corrected text is never used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from evaluate_text import aggregate, text_metrics


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
REPORTS = LAB / "reports"
CONFIGS = LAB / "configs"
DEFAULT_MODEL = ROOT / "sciobraille-scanner" / "backend" / "model" / "best.pt"
DEFAULT_DATA = ROOT / "prabh-decoders-braillevision" / "dataset" / "braille_merged" / "data.yaml"
DEFAULT_GT = LAB / "benchmark" / "ground_truth.csv"
SEARCH_CSV = REPORTS / "v1_inference_search.csv"

CONFIDENCES = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
IOUS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)
PREPROCESSING = (
    "raw",
    "current_production",
    "bilateral",
    "clahe",
    "clahe_bilateral",
    "illumination_normalization",
)


@dataclass(frozen=True)
class Config:
    confidence: float = 0.35
    iou: float = 0.45
    preprocessing: str = "current_production"
    tta: bool = False
    line_clustering: str = "adaptive"
    line_tolerance: float = 0.60
    spacing_multiplier: float = 1.80
    width_multiplier: float = 1.35
    duplicate_handling: str = "model_nms"
    duplicate_iou: float = 0.70
    flip_strategy: str = "benchmark_metadata"
    imgsz: int = 640


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / path).resolve()


def preprocess(image: np.ndarray, mode: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Return primary model input and optional zero-detection fallback."""
    if mode == "raw":
        return image, None
    if mode == "current_production":
        return cv2.bilateralFilter(image, 9, 75, 75), image
    if mode == "bilateral":
        return cv2.bilateralFilter(image, 7, 50, 50), None

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, channel_a, channel_b = cv2.split(lab)
    if mode in {"clahe", "clahe_bilateral"}:
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
        output = cv2.cvtColor(cv2.merge((enhanced, channel_a, channel_b)), cv2.COLOR_LAB2BGR)
        if mode == "clahe_bilateral":
            output = cv2.bilateralFilter(output, 7, 50, 50)
        return output, None
    if mode == "illumination_normalization":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        background = cv2.GaussianBlur(gray, (0, 0), sigmaX=21, sigmaY=21)
        normalized = cv2.divide(gray, background, scale=128)
        normalized = cv2.normalize(normalized, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR), None
    raise ValueError(f"Unknown preprocessing mode: {mode}")


def box_iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    x1 = max(left["x1"], right["x1"])
    y1 = max(left["y1"], right["y1"])
    x2 = min(left["x2"], right["x2"])
    y2 = min(left["y2"], right["y2"])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left["x2"] - left["x1"]) * max(0.0, left["y2"] - left["y1"])
    right_area = max(0.0, right["x2"] - right["x1"]) * max(0.0, right["y2"] - right["y1"])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def deduplicate(detections: list[dict[str, Any]], mode: str, threshold: float) -> list[dict[str, Any]]:
    if mode == "model_nms":
        return detections
    kept: list[dict[str, Any]] = []
    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        duplicate = False
        for existing in kept:
            same_class = detection["label"] == existing["label"]
            if mode == "class_aware" and not same_class:
                continue
            if box_iou(detection, existing) >= threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(detection)
    return kept


def cluster_lines(detections: list[dict[str, Any]], mode: str, tolerance: float) -> list[list[dict[str, Any]]]:
    if not detections:
        return []
    heights = [item["height"] for item in detections]
    scale = float(np.mean(heights) if mode == "adaptive" else np.median(heights))
    epsilon = max(4.0, scale * tolerance)
    ordered = sorted(detections, key=lambda item: item["y_center"])

    if mode == "legacy":
        lines: list[list[dict[str, Any]]] = [[ordered[0]]]
        for detection in ordered[1:]:
            if abs(detection["y_center"] - lines[-1][-1]["y_center"]) <= epsilon:
                lines[-1].append(detection)
            else:
                lines.append([detection])
        return lines

    lines = []
    for detection in ordered:
        candidates = []
        for index, line in enumerate(lines):
            center = float(np.median([item["y_center"] for item in line]))
            distance = abs(detection["y_center"] - center)
            if distance <= epsilon:
                candidates.append((distance, index))
        if candidates:
            lines[min(candidates)[1]].append(detection)
        else:
            lines.append([detection])
    return sorted(lines, key=lambda line: float(np.median([item["y_center"] for item in line])))


def labels_with_spaces(line: list[dict[str, Any]], spacing_multiplier: float, width_multiplier: float) -> list[str]:
    ordered = sorted(line, key=lambda item: item["x_center"])
    if len(ordered) < 2:
        return [item["label"] for item in ordered]
    gaps = [ordered[index + 1]["x_center"] - ordered[index]["x_center"] for index in range(len(ordered) - 1)]
    widths = [item["width"] for item in ordered]
    median_gap = float(np.median(gaps))
    compact = [gap for gap in gaps if gap <= median_gap * 1.25]
    cell_gap = float(np.median(compact)) if compact else median_gap
    threshold = max(cell_gap * spacing_multiplier, float(np.median(widths)) * width_multiplier)
    labels = [ordered[0]["label"]]
    for index, detection in enumerate(ordered[1:]):
        if gaps[index] > threshold:
            labels.append(" ")
        labels.append(detection["label"])
    return labels


def reconstruct(detections: list[dict[str, Any]], config: Config) -> str:
    detections = deduplicate(detections, config.duplicate_handling, config.duplicate_iou)
    lines = cluster_lines(detections, config.line_clustering, config.line_tolerance)
    output = []
    for line in lines:
        labels = labels_with_spaces(line, config.spacing_multiplier, config.width_multiplier)
        text = "".join(labels).strip().lower()
        if text:
            output.append(text)
    return "\n".join(output)


def parse_boxes(result: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    detections = []
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        detections.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "x_center": (x1 + x2) / 2,
                "y_center": (y1 + y2) / 2,
                "width": x2 - x1,
                "height": y2 - y1,
                "label": str(names[int(box.cls[0])]),
                "confidence": float(box.conf[0]),
            }
        )
    return detections


def orientation_candidates(image: np.ndarray, strategy: str, metadata_flip: bool) -> Iterable[tuple[bool, np.ndarray]]:
    if strategy == "benchmark_metadata":
        yield metadata_flip, cv2.flip(image, 1) if metadata_flip else image
    elif strategy == "never":
        yield False, image
    elif strategy == "always":
        yield True, cv2.flip(image, 1)
    elif strategy == "auto_detection_score":
        yield False, image
        yield True, cv2.flip(image, 1)
    else:
        raise ValueError(f"Unknown flip strategy: {strategy}")


def infer(model: YOLO, names: dict[int, str], image: np.ndarray, config: Config, metadata_flip: bool) -> dict[str, Any]:
    started = time.perf_counter()
    candidates = []
    for flipped, oriented in orientation_candidates(image, config.flip_strategy, metadata_flip):
        model_input, fallback = preprocess(oriented, config.preprocessing)
        result = model.predict(
            model_input,
            conf=config.confidence,
            iou=config.iou,
            imgsz=config.imgsz,
            augment=config.tta,
            verbose=False,
        )[0]
        if fallback is not None and len(result.boxes) == 0:
            result = model.predict(
                fallback,
                conf=config.confidence,
                iou=config.iou,
                imgsz=config.imgsz,
                augment=config.tta,
                verbose=False,
            )[0]
        detections = parse_boxes(result, names)
        score = len(detections) * (float(np.mean([item["confidence"] for item in detections])) if detections else 0.0)
        candidates.append((score, flipped, detections))
    _, flipped, detections = max(candidates, key=lambda item: item[0])
    return {
        "raw_text": reconstruct(detections, config),
        "detections": len(detections),
        "mean_confidence": float(np.mean([item["confidence"] for item in detections])) if detections else 0.0,
        "flipped": flipped,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
    }


def load_samples(path: Path) -> list[dict[str, Any]]:
    samples = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            image_path = resolve_path(row["image_path"])
            image = cv2.imread(str(image_path))
            if image is None:
                raise FileNotFoundError(f"Could not load benchmark image: {image_path}")
            flip = row.get("flip_horizontal", "").strip().lower()
            samples.append({**row, "image": image, "metadata_flip": flip in {"1", "true", "yes", "on"} if flip else True})
    return samples


def evaluate_config(
    model: YOLO,
    names: dict[int, str],
    samples: list[dict[str, Any]],
    config: Config,
    repeat: int = 1,
) -> dict[str, Any]:
    metric_rows = []
    latencies = []
    predictions = []
    for sample in samples:
        outputs = [infer(model, names, sample["image"], config, sample["metadata_flip"]) for _ in range(max(1, repeat))]
        output = outputs[-1]
        metrics = text_metrics(sample["ground_truth"], output["raw_text"])
        metric_rows.append(metrics)
        latencies.extend(item["latency_ms"] for item in outputs)
        predictions.append(
            {
                "id": sample["id"],
                "raw_text": output["raw_text"],
                "detections": output["detections"],
                "mean_confidence": output["mean_confidence"],
                "flipped": output["flipped"],
                "cer": metrics["cer"],
                "wer": metrics["wer"],
            }
        )
    summary = aggregate(metric_rows)
    summary.update(
        {
            "average_latency_ms": sum(latencies) / len(latencies),
            "median_latency_ms": statistics.median(latencies),
            "objective": (float(summary["cer"]) + float(summary["wer"])) / 2,
            "predictions_json": json.dumps(predictions, ensure_ascii=True),
        }
    )
    return summary


def detection_validation(model: YOLO, data: Path, config: Config, name: str) -> dict[str, Any]:
    result = model.val(
        data=str(data),
        split="val",
        conf=config.confidence,
        iou=config.iou,
        imgsz=config.imgsz,
        augment=config.tta,
        verbose=False,
        plots=False,
        project=str(REPORTS / "ultralytics" / "v1_inference_search"),
        name=name,
        exist_ok=True,
    )
    return {
        "precision": float(result.box.mp),
        "recall": float(result.box.mr),
        "map50": float(result.box.map50),
        "map50_95": float(result.box.map),
    }


def rank_key(row: dict[str, Any]) -> tuple[float, float, float]:
    return float(row["objective"]), float(row["cer"]), float(row["average_latency_ms"])


def same_config(row: dict[str, Any], config: Config) -> bool:
    for key, expected in asdict(config).items():
        actual = row.get(key)
        if isinstance(expected, bool):
            if str(actual).lower() not in {str(expected).lower(), str(int(expected))}:
                return False
        elif isinstance(expected, float):
            if abs(float(actual) - expected) > 1e-9:
                return False
        elif isinstance(expected, int):
            if int(float(actual)) != expected:
                return False
        elif str(actual) != str(expected):
            return False
    return True


def load_search_csv() -> list[dict[str, Any]]:
    if not SEARCH_CSV.exists():
        return []
    with SEARCH_CSV.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def config_from_row(row: dict[str, Any]) -> Config:
    defaults = Config()
    values: dict[str, Any] = {}
    for key, default in asdict(defaults).items():
        raw = row[key]
        if isinstance(default, bool):
            values[key] = str(raw).lower() in {"1", "true", "yes", "on"}
        elif isinstance(default, float):
            values[key] = float(raw)
        elif isinstance(default, int):
            values[key] = int(float(raw))
        else:
            values[key] = raw
    return Config(**values)


def run_candidate(
    model: YOLO,
    names: dict[int, str],
    samples: list[dict[str, Any]],
    stage: str,
    config: Config,
    rows: list[dict[str, Any]],
    data: Path | None = None,
    repeat: int = 1,
) -> dict[str, Any]:
    for existing in rows:
        if existing.get("stage") == stage and same_config(existing, config):
            print(f"{stage:20s} resume existing configuration")
            return existing
    metrics = evaluate_config(model, names, samples, config, repeat=repeat)
    row = {"stage": stage, **asdict(config), **metrics, "precision": "", "recall": "", "map50": "", "map50_95": ""}
    if data is not None:
        detector_match = next(
            (
                existing
                for existing in rows
                if existing.get("recall") not in {None, ""}
                and all(
                    str(existing.get(key)).lower() == str(value).lower()
                    for key, value in {
                        "confidence": config.confidence,
                        "iou": config.iou,
                        "preprocessing": config.preprocessing,
                        "tta": config.tta,
                        "imgsz": config.imgsz,
                    }.items()
                )
            ),
            None,
        )
        if detector_match:
            row.update({key: detector_match[key] for key in ("precision", "recall", "map50", "map50_95")})
        else:
            validation = detection_validation(model, data, config, f"{stage}_{len(rows):03d}")
            row.update(validation)
    rows.append(row)
    write_search_csv(rows)
    print(
        f"{stage:20s} conf={config.confidence:.2f} iou={config.iou:.2f} "
        f"pre={config.preprocessing:26s} tta={int(config.tta)} "
        f"CER={row['cer']:.4f} WER={row['wer']:.4f} latency={row['average_latency_ms']:.1f}ms"
    )
    return row


def write_search_csv(rows: list[dict[str, Any]]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "stage", *Config.__dataclass_fields__.keys(), "sample_count", "cer", "wer", "character_accuracy",
        "word_accuracy", "exact_sentence_accuracy", "average_latency_ms", "median_latency_ms", "objective",
        "precision", "recall", "map50", "map50_95", "predictions_json",
    ]
    with SEARCH_CSV.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def unique_configs(configs: Iterable[Config]) -> list[Config]:
    return list(dict.fromkeys(configs))


def write_outputs(best: dict[str, Any], rows: list[dict[str, Any]], model: Path, model_hash: str, sample_count: int) -> None:
    best_config = asdict(config_from_row(best))
    def number(value: Any) -> float | None:
        return None if value in {None, ""} else float(value)

    payload = {
        "version": 1,
        "purpose": "Sciobraille V1 inference-only optimization",
        "model": {"path": str(model), "sha256": model_hash},
        "accuracy_source": "raw_text only",
        "benchmark_samples": sample_count,
        "configuration": best_config,
        "benchmark": {
            "cer": number(best["cer"]),
            "wer": number(best["wer"]),
            "character_accuracy": number(best["character_accuracy"]),
            "word_accuracy": number(best["word_accuracy"]),
            "exact_sentence_accuracy": number(best["exact_sentence_accuracy"]),
            "average_latency_ms": number(best["average_latency_ms"]),
            "median_latency_ms": number(best["median_latency_ms"]),
            "precision": number(best["precision"]),
            "recall": number(best["recall"]),
            "map50": number(best["map50"]),
            "map50_95": number(best["map50_95"]),
        },
    }
    CONFIGS.mkdir(parents=True, exist_ok=True)
    (CONFIGS / "v1_optimized.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    baseline = json.loads((REPORTS / "v1_original_baseline.json").read_text(encoding="utf-8"))
    original = baseline["text_metrics"]
    lines = [
        "# Sciobraille V1 Inference Optimization",
        "",
        "Inference-only staged search. Production model and scanner code were not modified. No training performed.",
        "",
        "## Selection Rule",
        "",
            "Primary objective: lowest mean of raw CER and raw WER. Latency breaks close ties. Corrected text never affects scoring.",
            "Ground-truth-dependent `benchmark_metadata` flipping is excluded from final selection.",
        "",
        "## Best Configuration",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in best_config.items())
    lines.extend(
        [
            "",
            "## Result",
            "",
            f"- raw CER: `{best['cer']}` (original `{original['cer']}`)",
            f"- raw WER: `{best['wer']}` (original `{original['wer']}`)",
            f"- character accuracy: `{best['character_accuracy']}`",
            f"- word accuracy: `{best['word_accuracy']}`",
            f"- exact sentence accuracy: `{best['exact_sentence_accuracy']}`",
            f"- average latency ms: `{best['average_latency_ms']}` (original `{original['average_inference_latency_ms']}`)",
            f"- median latency ms: `{best['median_latency_ms']}` (original `{original['median_inference_latency_ms']}`)",
            f"- precision: `{best['precision']}`",
            f"- recall: `{best['recall']}`",
            f"- mAP50: `{best['map50']}`",
            f"- mAP50-95: `{best['map50_95']}`",
            "",
            "## Search",
            "",
            f"- configurations evaluated: `{len(rows)}`",
            "- stages: confidence, IoU, preprocessing/TTA, reconstruction, combined finalists",
            "- confidence values: `0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50`",
            "- IoU values: `0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60`",
            "- preprocessing: `raw, current_production, bilateral, clahe, clahe_bilateral, illumination_normalization`",
            "- full results: `reports/v1_inference_search.csv`",
            "",
            "## Limits",
            "",
            f"Only `{sample_count}` independent physical benchmark images exist. Configuration is provisional and likely overfit.",
            "Add 50-100 held-out physical phone-camera images before release gating or production adoption.",
            "Detection metrics use merged-dataset validation images, not independent physical images.",
            "",
            "## Integrity",
            "",
            f"- production model SHA256 before and after search: `{model_hash}`",
            "- production model overwritten: `false`",
            "- production scanner modified: `false`",
            "- training performed: `false`",
        ]
    )
    (REPORTS / "v1_inference_optimized.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tune Sciobraille inference without retraining")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--skip-detection", action="store_true", help="Skip slower YOLO validation metrics")
    parser.add_argument("--resume", action="store_true", help="Resume checkpointed search CSV")
    args = parser.parse_args()

    model_path = args.model.resolve()
    before_hash = sha256(model_path)
    model = YOLO(str(model_path))
    names = model.names
    samples = load_samples(args.ground_truth.resolve())
    rows: list[dict[str, Any]] = load_search_csv() if args.resume else []
    base = Config()

    # Stage 1A: confidence at production IoU.
    confidence_rows = [
        run_candidate(model, names, samples, "confidence", replace(base, confidence=value), rows, None if args.skip_detection else args.data)
        for value in CONFIDENCES
    ]
    best_conf = config_from_row(min(confidence_rows, key=rank_key))

    # Stage 1B: IoU at best confidence.
    iou_rows = [
        run_candidate(model, names, samples, "iou", replace(best_conf, iou=value), rows, None if args.skip_detection else args.data)
        for value in IOUS
    ]
    best_thresholds = config_from_row(min(iou_rows, key=rank_key))

    # Stage 2: preprocessing with TTA off/on.
    preprocessing_rows = []
    for mode in PREPROCESSING:
        for tta in (False, True):
            preprocessing_rows.append(
                run_candidate(model, names, samples, "preprocessing", replace(best_thresholds, preprocessing=mode, tta=tta), rows)
            )
    best_preprocessing = config_from_row(min(preprocessing_rows, key=rank_key))

    # Stage 3: isolate reconstruction choices.
    reconstruction_configs = []
    reconstruction_configs.extend(replace(best_preprocessing, line_clustering=mode, line_tolerance=tol) for mode, tol in (("legacy", 0.60), ("adaptive", 0.50), ("adaptive", 0.60), ("adaptive", 0.70)))
    reconstruction_configs.extend(replace(best_preprocessing, spacing_multiplier=value) for value in (1.50, 1.70, 1.80, 2.00, 2.20))
    reconstruction_configs.extend(replace(best_preprocessing, duplicate_handling=mode) for mode in ("model_nms", "class_aware", "class_agnostic"))
    reconstruction_configs.extend(replace(best_preprocessing, flip_strategy=mode) for mode in ("benchmark_metadata", "never", "always", "auto_detection_score"))
    reconstruction_rows = [run_candidate(model, names, samples, "reconstruction", config, rows) for config in unique_configs(reconstruction_configs)]

    # Stage 4: combine strongest independent choices, then validate finalists.
    best_line = min((row for row in reconstruction_rows if row["line_clustering"] != best_preprocessing.line_clustering or row["line_tolerance"] != best_preprocessing.line_tolerance), key=rank_key, default=min(reconstruction_rows, key=rank_key))
    best_space = min((row for row in reconstruction_rows if row["spacing_multiplier"] != best_preprocessing.spacing_multiplier), key=rank_key, default=min(reconstruction_rows, key=rank_key))
    best_duplicate = min((row for row in reconstruction_rows if row["duplicate_handling"] != best_preprocessing.duplicate_handling), key=rank_key, default=min(reconstruction_rows, key=rank_key))
    best_flip = min((row for row in reconstruction_rows if row["flip_strategy"] != best_preprocessing.flip_strategy), key=rank_key, default=min(reconstruction_rows, key=rank_key))
    combined = replace(
        best_preprocessing,
        line_clustering=best_line["line_clustering"],
        line_tolerance=float(best_line["line_tolerance"]),
        spacing_multiplier=float(best_space["spacing_multiplier"]),
        duplicate_handling=best_duplicate["duplicate_handling"],
        flip_strategy=best_flip["flip_strategy"],
    )
    finalist_configs = unique_configs(
        [
            best_thresholds,
            best_preprocessing,
            config_from_row(min(reconstruction_rows, key=rank_key)),
            combined,
        ]
    )
    finalist_rows = [
        run_candidate(model, names, samples, "finalist", config, rows, None if args.skip_detection else args.data)
        for config in finalist_configs
    ]
    preliminary_best = config_from_row(min(finalist_rows, key=rank_key))

    # Re-time meaningful finalists after warm-up. Detector metrics are reused.
    infer(model, names, samples[0]["image"], preliminary_best, samples[0]["metadata_flip"])
    verified_configs = unique_configs(
        [
            preliminary_best,
            replace(preliminary_best, flip_strategy="benchmark_metadata"),
            replace(preliminary_best, tta=False),
        ]
    )
    verified_rows = [
        run_candidate(
            model,
            names,
            samples,
            "finalist_repeated",
            config,
            rows,
            None if args.skip_detection else args.data,
            repeat=3,
        )
        for config in verified_configs
    ]
    deployable_rows = [row for row in verified_rows if row["flip_strategy"] != "benchmark_metadata"]
    best = min(deployable_rows or verified_rows, key=rank_key)

    after_hash = sha256(model_path)
    if after_hash != before_hash:
        raise RuntimeError("Production model hash changed during read-only tuning")
    write_outputs(best, rows, model_path, before_hash, len(samples))
    print(json.dumps({"best": {key: best[key] for key in [*Config.__dataclass_fields__, "cer", "wer", "average_latency_ms", "recall", "map50_95"]}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
