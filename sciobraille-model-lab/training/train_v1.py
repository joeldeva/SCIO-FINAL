#!/usr/bin/env python3
"""Train and finalize Sciobraille V1 Optimized.

Uses production weights as initialization, never as an output path. V1 uses only
the production model's original Prabh merged dataset lineage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import torch
import torch.nn.functional as functional
import ultralytics
import yaml
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
DEFAULT_CONFIG = LAB / "configs" / "train_v1.yaml"
PHOTO_CONFIG: dict[str, Any] = {}


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_fingerprint(data_yaml: Path) -> tuple[str, dict[str, int]]:
    data = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    dataset_root = resolve_path(data["path"])
    digest = hashlib.sha256()
    counts = {"images": 0, "labels": 0}
    paths = []
    for split in ("train", "val", "test"):
        split_value = data.get(split)
        if not split_value:
            continue
        image_dir = dataset_root / split_value
        label_dir = Path(str(image_dir).replace("images", "labels"))
        if image_dir.exists():
            paths.extend(path for path in image_dir.rglob("*") if path.is_file())
        if label_dir.exists():
            paths.extend(path for path in label_dir.rglob("*") if path.is_file())
    for path in sorted(set(paths), key=lambda item: item.as_posix().lower()):
        relative = path.relative_to(dataset_root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(file_sha256(path).encode("ascii"))
        if "images" in path.parts:
            counts["images"] += 1
        elif "labels" in path.parts:
            counts["labels"] += 1
    return digest.hexdigest(), counts


def _random_between(low: float, high: float, device: torch.device) -> torch.Tensor:
    return torch.empty((), device=device).uniform_(low, high)


def apply_photometric_augmentations(images: torch.Tensor) -> torch.Tensor:
    """Apply label-safe camera and lighting changes after geometric transforms."""
    if not PHOTO_CONFIG or not images.requires_grad and images.numel() == 0:
        return images
    output = images.clone()
    probability = float(PHOTO_CONFIG["probability"])
    for index in range(output.shape[0]):
        image = output[index : index + 1]
        device = image.device
        if torch.rand((), device=device) < probability:
            brightness = _random_between(
                1.0 - float(PHOTO_CONFIG["brightness_limit"]),
                1.0 + float(PHOTO_CONFIG["brightness_limit"]),
                device,
            )
            contrast = _random_between(
                1.0 - float(PHOTO_CONFIG["contrast_limit"]),
                1.0 + float(PHOTO_CONFIG["contrast_limit"]),
                device,
            )
            gamma = _random_between(float(PHOTO_CONFIG["gamma_min"]), float(PHOTO_CONFIG["gamma_max"]), device)
            mean = image.mean(dim=(2, 3), keepdim=True)
            image = ((image - mean) * contrast + mean) * brightness
            image = image.clamp(1e-4, 1.0).pow(gamma)

        if torch.rand((), device=device) < float(PHOTO_CONFIG["blur_probability"]):
            image = functional.avg_pool2d(image, kernel_size=3, stride=1, padding=1)

        if torch.rand((), device=device) < float(PHOTO_CONFIG["noise_probability"]):
            image = image + torch.randn_like(image) * float(PHOTO_CONFIG["noise_sigma"])

        if torch.rand((), device=device) < float(PHOTO_CONFIG["shadow_probability"]):
            height, width = image.shape[-2:]
            x_axis = torch.linspace(-1.0, 1.0, width, device=device).view(1, 1, 1, width)
            y_axis = torch.linspace(-1.0, 1.0, height, device=device).view(1, 1, height, 1)
            angle = _random_between(0.0, 6.283185307, device)
            offset = _random_between(-0.45, 0.45, device)
            field = torch.cos(angle) * x_axis + torch.sin(angle) * y_axis - offset
            softness = torch.sigmoid(field * 7.0)
            strength = _random_between(
                float(PHOTO_CONFIG["shadow_strength_min"]),
                float(PHOTO_CONFIG["shadow_strength_max"]),
                device,
            )
            image = image * (1.0 - softness * strength)
        output[index : index + 1] = image.clamp(0.0, 1.0)
    return output


class BrailleTrainer(DetectionTrainer):
    """Detection trainer with conservative embossed-Braille photometric changes."""

    def preprocess_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        batch = super().preprocess_batch(batch)
        batch["img"] = apply_photometric_augmentations(batch["img"])
        return batch


def environment_record() -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pytorch": str(torch.__version__),
        "ultralytics": ultralytics.__version__,
        "opencv": cv2.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def inference_config(path: Path):
    sys.path.insert(0, str(LAB / "scripts"))
    import tune_inference

    data = yaml.safe_load(path.read_text(encoding="utf-8"))["configuration"]
    return tune_inference, tune_inference.Config(**data)


def evaluate_candidate(
    weight: Path,
    benchmark_csv: Path,
    data_yaml: Path,
    inference_yaml: Path,
    repeat: int,
    validation_confidence: float,
    validation_iou: float,
    output: Path,
) -> dict[str, Any]:
    tuning, configuration = inference_config(inference_yaml)
    model = YOLO(str(weight))
    samples = tuning.load_samples(benchmark_csv)
    tuning.infer(model, model.names, samples[0]["image"], configuration, samples[0]["metadata_flip"])
    text = tuning.evaluate_config(model, model.names, samples, configuration, repeat=repeat)
    started = time.perf_counter()
    validation = model.val(
        data=str(data_yaml),
        split="val",
        conf=validation_confidence,
        iou=validation_iou,
        imgsz=configuration.imgsz,
        augment=False,
        verbose=False,
        plots=False,
        project=str(output / "validation"),
        name=weight.stem + "_" + file_sha256(weight)[:8],
        exist_ok=True,
    )
    return {
        "path": str(weight),
        "sha256": file_sha256(weight),
        "size_bytes": weight.stat().st_size,
        "raw_cer": text["cer"],
        "raw_wer": text["wer"],
        "character_accuracy": text["character_accuracy"],
        "word_accuracy": text["word_accuracy"],
        "exact_sentence_accuracy": text["exact_sentence_accuracy"],
        "average_latency_ms": text["average_latency_ms"],
        "median_latency_ms": text["median_latency_ms"],
        "predictions": json.loads(text["predictions_json"]),
        "precision": float(validation.box.mp),
        "recall": float(validation.box.mr),
        "map50": float(validation.box.map50),
        "map50_95": float(validation.box.map),
        "validation_seconds": time.perf_counter() - started,
    }


def selection_key(candidate: dict[str, Any]) -> tuple[float, float, float, float, float]:
    return (
        float(candidate["raw_cer"]),
        float(candidate["raw_wer"]),
        -float(candidate["recall"]),
        -float(candidate["map50_95"]),
        float(candidate["average_latency_ms"]),
    )


def unique_candidates(paths: list[Path]) -> list[Path]:
    unique: dict[str, Path] = {}
    for path in paths:
        if path.exists():
            unique.setdefault(file_sha256(path), path)
    return list(unique.values())


def summarize_training_run(run_dir: Path, maximum_epochs: int) -> dict[str, Any]:
    results_path = run_dir / "results.csv"
    if not results_path.exists():
        return {"epochs_completed": 0, "maximum_epochs": maximum_epochs, "results_csv": str(results_path)}
    with results_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    best = max(rows, key=lambda row: float(row["metrics/mAP50-95(B)"])) if rows else None
    latest = rows[-1] if rows else None
    return {
        "epochs_completed": len(rows),
        "maximum_epochs": maximum_epochs,
        "stopped_early": len(rows) < maximum_epochs,
        "elapsed_seconds": float(latest["time"]) if latest else None,
        "best_map50_95_epoch": int(best["epoch"]) if best else None,
        "best_map50_95": float(best["metrics/mAP50-95(B)"]) if best else None,
        "final_recall": float(latest["metrics/recall(B)"]) if latest else None,
        "final_map50": float(latest["metrics/mAP50(B)"]) if latest else None,
        "final_map50_95": float(latest["metrics/mAP50-95(B)"]) if latest else None,
        "results_csv": str(results_path),
    }


def write_final_report(output: Path, payload: dict[str, Any]) -> None:
    report = LAB / "reports" / "v1_final_comparison.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    selected = payload["selected"]
    lines = [
        "# Sciobraille V1 Final Comparison",
        "",
        "V1 uses the production checkpoint and its original Prabh merged dataset lineage only.",
        "Text accuracy uses raw text. Corrected text never affects selection.",
        "",
        "## Selected Candidate",
        "",
        f"- source: `{selected['path']}`",
        f"- SHA256: `{selected['sha256']}`",
        f"- raw CER: `{selected['raw_cer']}`",
        f"- raw WER: `{selected['raw_wer']}`",
        f"- recall: `{selected['recall']}`",
        f"- mAP50: `{selected['map50']}`",
        f"- mAP50-95: `{selected['map50_95']}`",
        f"- average latency ms: `{selected['average_latency_ms']}`",
        "",
        "## Candidate Comparison",
        "",
        "| Candidate | Raw CER | Raw WER | Recall | mAP50-95 | Latency ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for candidate in sorted(payload["candidates"], key=selection_key):
        lines.append(
            f"| `{Path(candidate['path']).name}` `{candidate['sha256'][:8]}` | "
            f"{candidate['raw_cer']:.6f} | {candidate['raw_wer']:.6f} | "
            f"{candidate['recall']:.6f} | {candidate['map50_95']:.6f} | "
            f"{candidate['average_latency_ms']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- initialization SHA256: `{payload['initialization']['sha256']}`",
            f"- dataset fingerprint: `{payload['dataset']['fingerprint']}`",
            f"- dataset images: `{payload['dataset']['counts']['images']}`",
            f"- dataset labels: `{payload['dataset']['counts']['labels']}`",
            f"- seed: `{payload['training']['seed']}`",
            f"- epochs completed: `{payload['training_results']['epochs_completed']}` of `{payload['training_results']['maximum_epochs']}`",
            f"- early stopping: `{payload['training_results']['stopped_early']}`",
            f"- training best mAP50-95: `{payload['training_results']['best_map50_95']}` at epoch `{payload['training_results']['best_map50_95_epoch']}`",
            f"- Python: `{payload['environment']['python']}`",
            f"- PyTorch: `{payload['environment']['pytorch']}`",
            f"- Ultralytics: `{payload['environment']['ultralytics']}`",
            f"- CUDA available: `{payload['environment']['cuda_available']}`",
            "",
            "## Safety",
            "",
            f"- production SHA256 after completion: `{payload['production_sha256_after']}`",
            "- production model overwritten: `false`",
            "- V2 merged dataset used: `false`",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Sciobraille V1 Optimized")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--evaluate-only", type=Path, help="Evaluate checkpoints from an existing Ultralytics run")
    parser.add_argument("--finalize-existing", action="store_true", help="Finish YAML/report generation from evaluation.json")
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths = config["paths"]
    initialization = resolve_path(paths["initialization"])
    data_yaml = resolve_path(paths["data"])
    benchmark = resolve_path(paths["benchmark"])
    inference_yaml = resolve_path(paths["inference_config"])
    output = resolve_path(paths["output"])
    expected_data = (ROOT / "prabh-decoders-braillevision" / "dataset" / "braille_merged" / "data.yaml").resolve()
    if data_yaml != expected_data:
        raise RuntimeError(f"V1 dataset lineage violation: expected {expected_data}, got {data_yaml}")
    if initialization == output / "best.pt" or initialization.is_relative_to(output):
        raise RuntimeError("V1 output must not contain production initialization checkpoint")
    output.mkdir(parents=True, exist_ok=True)

    if args.finalize_existing:
        evaluation_path = output / "evaluation.json"
        if not evaluation_path.exists():
            raise FileNotFoundError(f"Missing finalized evaluation: {evaluation_path}")
        payload = json.loads(evaluation_path.read_text(encoding="utf-8"))
        payload["training_results"] = summarize_training_run(
            Path(payload["run_dir"]), int(payload["training"]["epochs"])
        )
        evaluation_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (output / "config.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        write_final_report(output, payload)
        partial = output / "evaluation.partial.json"
        if partial.exists():
            partial.unlink()
        print(json.dumps({"status": "finalized", "final_model": payload["final_model"]}, indent=2))
        return 0

    production_hash = file_sha256(initialization)
    dataset_hash, dataset_counts = dataset_fingerprint(data_yaml)
    global PHOTO_CONFIG
    PHOTO_CONFIG = config["photometric_augmentations"]

    if args.evaluate_only:
        run_dir = args.evaluate_only.resolve()
    else:
        training = config["training"]
        geometric = config["geometric_augmentations"]
        photometric = config["photometric_augmentations"]
        run_name = datetime.now().strftime("train_%Y%m%d_%H%M%S")
        model = YOLO(str(initialization))
        model.train(
            trainer=BrailleTrainer,
            data=str(data_yaml),
            project=str(output / "runs"),
            name=run_name,
            exist_ok=False,
            epochs=int(training["epochs"]),
            patience=int(training["patience"]),
            batch=int(training["batch"]),
            imgsz=int(training["imgsz"]),
            device=str(training["device"]),
            workers=int(training["workers"]),
            optimizer=str(training["optimizer"]),
            lr0=float(training["lr0"]),
            lrf=float(training["lrf"]),
            momentum=float(training["momentum"]),
            weight_decay=float(training["weight_decay"]),
            warmup_epochs=float(training["warmup_epochs"]),
            warmup_momentum=float(training["warmup_momentum"]),
            warmup_bias_lr=float(training["warmup_bias_lr"]),
            freeze=int(training["freeze"]),
            seed=int(training["seed"]),
            deterministic=bool(training["deterministic"]),
            amp=bool(training["amp"]),
            cache=bool(training["cache"]),
            save=True,
            save_period=int(training["save_period"]),
            close_mosaic=int(training["close_mosaic"]),
            val=True,
            plots=True,
            hsv_h=float(photometric["hsv_h"]),
            hsv_s=float(photometric["hsv_s"]),
            hsv_v=float(photometric["hsv_v"]),
            degrees=float(geometric["degrees"]),
            translate=float(geometric["translate"]),
            scale=float(geometric["scale"]),
            shear=float(geometric["shear"]),
            perspective=float(geometric["perspective"]),
            flipud=0.0,
            fliplr=0.0,
            mosaic=float(geometric["mosaic"]),
            mixup=0.0,
            cutmix=0.0,
            copy_paste=0.0,
        )
        run_dir = Path(model.trainer.save_dir).resolve()

    evaluation = config["evaluation"]
    candidate_paths = [initialization]
    for pattern in evaluation["candidate_globs"]:
        candidate_paths.extend(run_dir.glob(pattern))
    candidate_paths = unique_candidates(candidate_paths)
    if len(candidate_paths) < 2:
        raise RuntimeError(f"No trained candidate checkpoints found under {run_dir}")

    candidates = []
    for candidate_path in candidate_paths:
        print(f"Evaluating {candidate_path}", flush=True)
        candidates.append(
            evaluate_candidate(
                candidate_path,
                benchmark,
                data_yaml,
                inference_yaml,
                int(evaluation["text_repeat"]),
                float(evaluation["validation_confidence"]),
                float(evaluation["validation_iou"]),
                output,
            )
        )
        (output / "evaluation.partial.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    selected = min(candidates, key=selection_key)
    selected_path = Path(selected["path"])
    final_path = output / "best.pt"
    temporary_path = output / "best.pt.tmp"
    shutil.copy2(selected_path, temporary_path)
    if file_sha256(temporary_path) != selected["sha256"]:
        raise RuntimeError("Copied V1 checkpoint failed SHA256 verification")
    os.replace(temporary_path, final_path)

    production_hash_after = file_sha256(initialization)
    if production_hash_after != production_hash:
        raise RuntimeError("Production model changed during V1 training")

    payload = {
        "version": 1,
        "status": "finalized",
        "initialization": {"path": str(initialization), "sha256": production_hash},
        "dataset": {
            "data_yaml": str(data_yaml),
            "data_yaml_sha256": file_sha256(data_yaml),
            "fingerprint": dataset_hash,
            "counts": dataset_counts,
            "lineage": "prabh-decoders-braillevision/dataset/braille_merged only",
        },
        "environment": environment_record(),
        "training": config["training"],
        "training_results": summarize_training_run(run_dir, int(config["training"]["epochs"])),
        "geometric_augmentations": config["geometric_augmentations"],
        "photometric_augmentations": config["photometric_augmentations"],
        "run_dir": str(run_dir),
        "selection_priority": evaluation["selection_priority"],
        "selected": selected,
        "final_model": {"path": str(final_path), "sha256": file_sha256(final_path)},
        "candidates": candidates,
        "production_sha256_after": production_hash_after,
    }
    (output / "evaluation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    safe_payload = json.loads(json.dumps(payload, default=str))
    (output / "config.yaml").write_text(yaml.safe_dump(safe_payload, sort_keys=False), encoding="utf-8")
    write_final_report(output, payload)
    partial = output / "evaluation.partial.json"
    if partial.exists():
        partial.unlink()
    print(json.dumps({"selected": selected, "final_model": payload["final_model"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
