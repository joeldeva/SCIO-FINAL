#!/usr/bin/env python3
"""Train, validate, select, and report Sciobraille V2 Master models.

Trains two comparable candidates on Master V2:
  - Candidate A: YOLOv8s initialized from production weights
  - Candidate B: YOLO11s initialized from pretrained weights

Maintains safety:
  - Production model is NEVER overwritten.
  - Production model SHA256 is verified before and after execution.
  - Embossed-Braille augmentations never invert horizontal/vertical orientation.
  - Evaluation uses Master V2 validation split for selection.
  - Master V2 internal test split is evaluated only after selection.
  - Text metrics use raw OCR text only without spelling correction.
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
import numpy as np
import torch
import torch.nn.functional as functional
import ultralytics
import yaml
from ultralytics import YOLO
from ultralytics.models.yolo.detect import DetectionTrainer

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "sciobraille-model-lab"
SCRIPTS = LAB / "scripts"
REPORTS = LAB / "reports"
DEFAULT_CONFIG = LAB / "configs" / "train_v2.yaml"
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
    dataset_root = resolve_path(data.get("path", data_yaml.parent))
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
    """Detection trainer with embossed-Braille photometric augmentations."""

    def preprocess_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        batch = super().preprocess_batch(batch)
        batch["img"] = apply_photometric_augmentations(batch["img"])
        return batch


def environment_record() -> dict[str, Any]:
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None"
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3) if torch.cuda.is_available() else 0.0
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pytorch": str(torch.__version__),
        "ultralytics": ultralytics.__version__,
        "opencv": cv2.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "cuda_device": gpu_name,
        "cuda_vram_gb": round(vram_gb, 2),
    }


def summarize_training_run(run_dir: Path, maximum_epochs: int) -> dict[str, Any]:
    results_path = run_dir / "results.csv"
    if not results_path.exists():
        return {"epochs_completed": 0, "maximum_epochs": maximum_epochs, "results_csv": str(results_path)}
    with results_path.open("r", encoding="utf-8-sig", newline="") as stream:
        raw_rows = list(csv.DictReader(stream))
    rows = [{k.strip(): v.strip() for k, v in row.items() if k is not None} for row in raw_rows]
    best = max(rows, key=lambda row: float(row.get("metrics/mAP50-95(B)", 0.0))) if rows else None
    latest = rows[-1] if rows else None
    return {
        "epochs_completed": len(rows),
        "maximum_epochs": maximum_epochs,
        "stopped_early": len(rows) < maximum_epochs,
        "best_map50_95_epoch": int(best["epoch"]) if best and "epoch" in best else None,
        "best_map50_95": float(best["metrics/mAP50-95(B)"]) if best and "metrics/mAP50-95(B)" in best else None,
        "final_precision": float(latest["metrics/precision(B)"]) if latest and "metrics/precision(B)" in latest else None,
        "final_recall": float(latest["metrics/recall(B)"]) if latest and "metrics/recall(B)" in latest else None,
        "final_map50": float(latest["metrics/mAP50(B)"]) if latest and "metrics/mAP50(B)" in latest else None,
        "final_map50_95": float(latest["metrics/mAP50-95(B)"]) if latest and "metrics/mAP50-95(B)" in latest else None,
        "results_csv": str(results_path),
    }


def evaluate_split(
    model: YOLO,
    data_yaml: Path,
    split: str,
    output_dir: Path,
    conf: float = 0.001,
    iou: float = 0.70,
    imgsz: int = 640,
) -> dict[str, Any]:
    started = time.perf_counter()
    metrics = model.val(
        data=str(data_yaml),
        split=split,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        augment=False,
        verbose=False,
        plots=False,
        workers=0,
        project=str(output_dir / f"val_{split}"),
        name=f"eval_{split}",
        exist_ok=True,
    )
    duration = time.perf_counter() - started
    return {
        "split": split,
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
        "evaluation_seconds": duration,
    }


def measure_inference_latency(model: YOLO, imgsz: int = 640, warmups: int = 5, runs: int = 20) -> dict[str, float]:
    dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
    for _ in range(warmups):
        model.predict(dummy, imgsz=imgsz, verbose=False)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        model.predict(dummy, imgsz=imgsz, verbose=False)
        times.append((time.perf_counter() - t0) * 1000.0)
    return {
        "average_latency_ms": round(float(np.mean(times)), 2),
        "median_latency_ms": round(float(np.median(times)), 2),
        "std_latency_ms": round(float(np.std(times)), 2),
    }


def evaluate_frozen_benchmark(
    weight: Path,
    benchmark_csv: Path,
    inference_yaml: Path,
) -> dict[str, Any]:
    sys.path.insert(0, str(SCRIPTS))
    import tune_inference

    data = yaml.safe_load(inference_yaml.read_text(encoding="utf-8"))["configuration"]
    configuration = tune_inference.Config(**data)
    model = YOLO(str(weight))
    samples = tune_inference.load_samples(benchmark_csv)
    if not samples:
        return {"cer": 1.0, "wer": 1.0, "character_accuracy": 0.0, "word_accuracy": 0.0}
    # Warmup
    tune_inference.infer(model, model.names, samples[0]["image"], configuration, samples[0]["metadata_flip"])
    text_eval = tune_inference.evaluate_config(model, model.names, samples, configuration, repeat=1)
    return {
        "cer": float(text_eval["cer"]),
        "wer": float(text_eval["wer"]),
        "character_accuracy": float(text_eval["character_accuracy"]),
        "word_accuracy": float(text_eval["word_accuracy"]),
        "exact_sentence_accuracy": float(text_eval["exact_sentence_accuracy"]),
    }


def train_candidate(
    candidate_key: str,
    candidate_cfg: dict[str, Any],
    config: dict[str, Any],
    data_yaml: Path,
) -> dict[str, Any]:
    training = config["training"]
    geometric = config["geometric_augmentations"]
    photometric = config["photometric_augmentations"]

    arch = candidate_cfg["arch"]
    init_path = resolve_path(candidate_cfg["initialization"])
    exp_dir = resolve_path(candidate_cfg["experiment_dir"])
    exp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================", flush=True)
    print(f"Starting Training: {candidate_cfg['name']} ({arch})", flush=True)
    print(f"Initialization: {init_path} (SHA: {file_sha256(init_path)[:12]})", flush=True)
    print(f"Output Experiment Directory: {exp_dir}", flush=True)
    print(f"=======================================================\n", flush=True)

    last_pt = exp_dir / "weights" / "last.pt"
    best_pt = exp_dir / "weights" / "best.pt"
    results_csv = exp_dir / "results.csv"

    # Check if run can be resumed or is already completed
    is_complete = False
    if results_csv.exists() and best_pt.exists():
        with results_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            r_rows = list(csv.DictReader(stream))
        if len(r_rows) >= int(training["epochs"]):
            is_complete = True

    if is_complete:
        print(f"Candidate {candidate_cfg['name']} already completed {len(r_rows)} epochs. Reusing existing checkpoint.", flush=True)
        run_dir = exp_dir
    elif last_pt.exists():
        print(f"Resuming Candidate {candidate_cfg['name']} from {last_pt}...", flush=True)
        model = YOLO(str(last_pt))
        model.train(resume=True)
        run_dir = exp_dir
    else:
        model = YOLO(str(init_path))

        # Verify class count
        if hasattr(model, "names") and model.names:
            print(f"Initial model names count: {len(model.names)}", flush=True)

        model.train(
            trainer=BrailleTrainer,
            data=str(data_yaml),
            project=str(exp_dir.parent),
            name=exp_dir.name,
            exist_ok=True,
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

    best_pt = run_dir / "weights" / "best.pt"
    if not best_pt.exists():
        raise RuntimeError(f"Expected best checkpoint not found at {best_pt}")

    summary = summarize_training_run(run_dir, int(training["epochs"]))

    # Validation evaluation on Master V2 val split
    val_model = YOLO(str(best_pt))
    val_metrics = evaluate_split(
        val_model,
        data_yaml,
        split="val",
        output_dir=run_dir,
        conf=float(config["evaluation"]["validation_confidence"]),
        iou=float(config["evaluation"]["validation_iou"]),
        imgsz=int(training["imgsz"]),
    )

    # Latency measurement
    latency = measure_inference_latency(val_model, imgsz=int(training["imgsz"]))

    return {
        "key": candidate_key,
        "name": candidate_cfg["name"],
        "arch": arch,
        "initialization": {"path": str(init_path), "sha256": file_sha256(init_path)},
        "run_dir": str(run_dir),
        "best_checkpoint": str(best_pt),
        "best_checkpoint_sha256": file_sha256(best_pt),
        "best_checkpoint_size_bytes": best_pt.stat().st_size,
        "training_summary": summary,
        "validation_metrics": val_metrics,
        "latency": latency,
    }


def generate_reports(
    config: dict[str, Any],
    dataset_info: dict[str, Any],
    env: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    selected: dict[str, Any],
    v1_comparison: dict[str, Any],
    output_root: Path,
) -> None:
    # 1. v2_training_report.md
    train_report_path = REPORTS / "v2_training_report.md"
    lines = [
        "# Sciobraille V2 Training Report",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## 1. Environment & Hardware",
        "",
        f"- **Platform:** `{env['platform']}`",
        f"- **Python:** `{env['python']}`",
        f"- **PyTorch:** `{env['pytorch']}`",
        f"- **Ultralytics:** `{env['ultralytics']}`",
        f"- **CUDA Available:** `{env['cuda_available']}`",
        f"- **CUDA Device:** `{env['cuda_device']}` ({env.get('cuda_vram_gb', 0)} GB VRAM)",
        "",
        "## 2. Dataset Lineage & Splits",
        "",
        f"- **Dataset Path:** `{dataset_info['data_yaml']}`",
        f"- **Dataset Fingerprint (SHA-256):** `{dataset_info['fingerprint']}`",
        f"- **Retained Images:** `{dataset_info['counts']['images']}`",
        f"- **Bounding Boxes:** `{dataset_info['counts']['labels']}`",
        f"- **Train Images:** 1440",
        f"- **Validation Images:** 165",
        f"- **Internal Test Images:** 179",
        "- **Canonical Classes:** 26 (`0=a` through `25=z`)",
        "",
        "## 3. Augmentation Strategy (Embossed-Braille Safe)",
        "",
        "- **Geometric:** `flipud=0.0`, `fliplr=0.0` (preserves dot semantics), `degrees=3.0`, `scale=0.12`, `mosaic=0.10`",
        "- **Photometric:** Brightness +/-10%, Contrast +/-12%, Gamma [0.92, 1.08], Blur p=0.08, Noise p=0.10, Shadow p=0.10",
        "",
        "## 4. Trained Candidates Summary",
        "",
        "| Candidate | Architecture | Epochs | Best Val mAP50-95 | Best Val mAP50 | Best Val Recall | Precision | Latency (ms) | Checkpoint SHA-256 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for c in candidate_results:
        vm = c["validation_metrics"]
        lat = c["latency"]
        lines.append(
            f"| `{c['name']}` | {c['arch']} | {c['training_summary']['epochs_completed']} | "
            f"**{vm['map50_95']:.4f}** | {vm['map50']:.4f} | {vm['recall']:.4f} | {vm['precision']:.4f} | "
            f"{lat['average_latency_ms']} ms | `{c['best_checkpoint_sha256'][:12]}` |"
        )
    lines.extend([
        "",
        "## 5. Checkpoint Selection",
        "",
        f"- **Selected Architecture:** `{selected['arch']}` (`{selected['name']}`)",
        f"- **Selected Checkpoint:** `{selected['best_checkpoint']}`",
        f"- **Selected Checkpoint SHA-256:** `{selected['best_checkpoint_sha256']}`",
        f"- **Selection Criteria:** Maximizing validation `mAP50-95` on Master V2 validation split.",
        f"- **Destination:** `{output_root / 'best.pt'}`",
    ])
    train_report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {train_report_path}")

    # 2. v2_model_comparison.md
    comp_report_path = REPORTS / "v2_model_comparison.md"
    lines2 = [
        "# Sciobraille V2 Model Comparison (Candidate A vs Candidate B)",
        "",
        "Comparative evaluation of V2 candidate architectures trained on Master V2 under identical conditions.",
        "",
        "## Candidate Configurations",
        "",
        "1. **Candidate A (YOLOv8s):** Initialized from production Model B weights (`sciobraille-scanner/backend/model/best.pt`).",
        "2. **Candidate B (YOLO11s):** Initialized from official pre-trained COCO weights (`yolo11s.pt`).",
        "",
        "## Validation Metrics (Master V2 Validation Split: 165 images)",
        "",
        "| Metric | Candidate A (YOLOv8s) | Candidate B (YOLO11s) | Difference (B - A) |",
        "|---|---:|---:|---:|",
    ]
    c_a = candidate_results[0]
    c_b = candidate_results[1]
    va = c_a["validation_metrics"]
    vb = c_b["validation_metrics"]
    lines2.extend([
        f"| **mAP50-95** | {va['map50_95']:.4f} | {vb['map50_95']:.4f} | {vb['map50_95'] - va['map50_95']:+.4f} |",
        f"| **mAP50** | {va['map50']:.4f} | {vb['map50']:.4f} | {vb['map50'] - va['map50']:+.4f} |",
        f"| **Recall** | {va['recall']:.4f} | {vb['recall']:.4f} | {vb['recall'] - va['recall']:+.4f} |",
        f"| **Precision** | {va['precision']:.4f} | {vb['precision']:.4f} | {vb['precision'] - va['precision']:+.4f} |",
        f"| **Inference Latency** | {c_a['latency']['average_latency_ms']} ms | {c_b['latency']['average_latency_ms']} ms | {c_b['latency']['average_latency_ms'] - c_a['latency']['average_latency_ms']:+.2f} ms |",
        f"| **Model Size** | {c_a['best_checkpoint_size_bytes'] / (1024*1024):.2f} MB | {c_b['best_checkpoint_size_bytes'] / (1024*1024):.2f} MB | {(c_b['best_checkpoint_size_bytes'] - c_a['best_checkpoint_size_bytes']) / (1024*1024):+.2f} MB |",
        "",
        "## Analysis & Recommendation",
        "",
        f"The candidate selected for Sciobraille V2 Master is **{selected['name']} ({selected['arch']})**.",
        f"Validation mAP50-95 reached **{selected['validation_metrics']['map50_95']:.4f}**.",
    ])
    comp_report_path.write_text("\n".join(lines2), encoding="utf-8")
    print(f"Generated {comp_report_path}")

    # 3. final_model_comparison.md
    final_comp_path = REPORTS / "final_model_comparison.md"
    v1 = v1_comparison
    v2 = selected
    lines3 = [
        "# Sciobraille Final Model Comparison: V1 Production vs V2 Master",
        "",
        "Head-to-head comparison between active production V1 model and newly trained V2 Master model under equivalent evaluation conditions on the Master V2 dataset.",
        "",
        "## Model Identification",
        "",
        "| Attribute | Production V1 | Master V2 Winner |",
        "|---|---|---|",
        f"| **Architecture** | YOLOv8s | {v2['arch']} |",
        f"| **Checkpoint Path** | `sciobraille-scanner/backend/model/best.pt` | `sciobraille-model-lab/models/v2_master/best.pt` |",
        f"| **SHA-256** | `{v1['sha256']}` | `{v2['best_checkpoint_sha256']}` |",
        f"| **Training Dataset** | Prabh merged (1,614 images) | Master V2 (1,784 unique images, 99,352 boxes) |",
        f"| **Model Size** | {v1['size_bytes'] / (1024*1024):.2f} MB | {v2['best_checkpoint_size_bytes'] / (1024*1024):.2f} MB |",
        "",
        "## Evaluation Metrics on Master V2 Validation Split (165 images)",
        "",
        "| Metric | Production V1 Baseline | Master V2 Winner | Delta (V2 - V1) |",
        "|---|---:|---:|---:|",
        f"| **mAP50-95** | {v1['val_metrics']['map50_95']:.4f} | {v2['validation_metrics']['map50_95']:.4f} | {v2['validation_metrics']['map50_95'] - v1['val_metrics']['map50_95']:+.4f} |",
        f"| **mAP50** | {v1['val_metrics']['map50']:.4f} | {v2['validation_metrics']['map50']:.4f} | {v2['validation_metrics']['map50'] - v1['val_metrics']['map50']:+.4f} |",
        f"| **Recall** | {v1['val_metrics']['recall']:.4f} | {v2['validation_metrics']['recall']:.4f} | {v2['validation_metrics']['recall'] - v1['val_metrics']['recall']:+.4f} |",
        f"| **Precision** | {v1['val_metrics']['precision']:.4f} | {v2['validation_metrics']['precision']:.4f} | {v2['validation_metrics']['precision'] - v1['val_metrics']['precision']:+.4f} |",
        f"| **Inference Latency** | {v1['latency']['average_latency_ms']:.2f} ms | {v2['latency']['average_latency_ms']:.2f} ms | {v2['latency']['average_latency_ms'] - v1['latency']['average_latency_ms']:+.2f} ms |",
        "",
        "## Internal Test Split Evaluation (179 images - Unbiased Post-Selection)",
        "",
        "| Metric | Production V1 | Master V2 Winner | Delta (V2 - V1) |",
        "|---|---:|---:|---:|",
        f"| **Test mAP50-95** | {v1['test_metrics']['map50_95']:.4f} | {v2['test_metrics']['map50_95']:.4f} | {v2['test_metrics']['map50_95'] - v1['test_metrics']['map50_95']:+.4f} |",
        f"| **Test mAP50** | {v1['test_metrics']['map50']:.4f} | {v2['test_metrics']['map50']:.4f} | {v2['test_metrics']['map50'] - v1['test_metrics']['map50']:+.4f} |",
        f"| **Test Recall** | {v1['test_metrics']['recall']:.4f} | {v2['test_metrics']['recall']:.4f} | {v2['test_metrics']['recall'] - v1['test_metrics']['recall']:+.4f} |",
        f"| **Test Precision** | {v1['test_metrics']['precision']:.4f} | {v2['test_metrics']['precision']:.4f} | {v2['test_metrics']['precision'] - v1['test_metrics']['precision']:+.4f} |",
        "",
        "## Physical Benchmark (3 Samples - Regression Check Only)",
        "",
        "| Metric | Production V1 | Master V2 Winner |",
        "|---|---:|---:|",
        f"| **Raw CER** | {v1['benchmark_metrics']['cer']:.4f} | {v2['benchmark_metrics']['cer']:.4f} |",
        f"| **Raw WER** | {v1['benchmark_metrics']['wer']:.4f} | {v2['benchmark_metrics']['wer']:.4f} |",
        f"| **Raw Character Accuracy** | {v1['benchmark_metrics']['character_accuracy']:.4f} | {v2['benchmark_metrics']['character_accuracy']:.4f} |",
        f"| **Raw Word Accuracy** | {v1['benchmark_metrics']['word_accuracy']:.4f} | {v2['benchmark_metrics']['word_accuracy']:.4f} |",
        "",
        "> [!IMPORTANT]",
        "> The 3-image physical benchmark is preserved for regression testing only and is insufficient for real-world certification. Real-world physical performance remains provisional pending collection of 50-100 independent field samples.",
    ]
    final_comp_path.write_text("\n".join(lines3), encoding="utf-8")
    print(f"Generated {final_comp_path}")

    # 4. remaining_work.md
    remaining_path = REPORTS / "remaining_work.md"
    lines4 = [
        "# Sciobraille Remaining Work Before Production Integration",
        "",
        "The Sciobraille V2 Master model has been trained, validated, and evaluated. Before deploying V2 into production (replacing `sciobraille-scanner/backend/model/best.pt` and updating Android assets), the following engineering tasks remain:",
        "",
        "## 1. Independent Physical Benchmark Collection",
        "- Collect 50-100 high-resolution physical Braille camera captures from diverse physical documents.",
        "- Cover varying lighting, blur, tilt/perspective, camera distance, and both front/reverse embossed paper.",
        "- Provide human-verified ground-truth English transcriptions without spelling correction using `independent_physical_schema.py`.",
        "",
        "## 2. Edge & Mobile Export Verification",
        "- Export selected V2 model to ONNX with dynamic batching.",
        "- Export to INT8 quantized TFLite (`best_int8.tflite`) for mobile offline inference.",
        "- Verify that LiteRT/TFLite inference latency and bounding box accuracy on real Android test devices match desktop PT baseline.",
        "",
        "## 3. End-to-End System & Camera Testing",
        "- Perform camera test on physical Android hardware across diverse device specifications.",
        "- Test automatic orientation / horizontal flip detection under user hand-held scanning.",
        "- Validate scanner WebSocket throughput and memory stability under continuous 30-FPS frame streaming.",
        "",
        "## 4. Production Release Approval",
        "- Review final model comparison with team stakeholders.",
        "- Archive rollback weights and commit formal production model replacement.",
    ]
    remaining_path.write_text("\n".join(lines4), encoding="utf-8")
    print(f"Generated {remaining_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sciobraille V2 Training and Validation Pipeline")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    # Safety checks
    prod_path = resolve_path(config["safety"]["production_model_path"])
    expected_prod_sha = config["safety"]["expected_production_sha256"]
    actual_prod_sha = file_sha256(prod_path)
    if actual_prod_sha != expected_prod_sha:
        raise RuntimeError(
            f"SAFETY VIOLATION: Production model SHA-256 mismatch!\nExpected: {expected_prod_sha}\nActual:   {actual_prod_sha}"
        )

    data_yaml = resolve_path(config["paths"]["data"])
    benchmark_csv = resolve_path(config["paths"]["benchmark"])
    inference_yaml = resolve_path(config["paths"]["inference_config"])
    output_root = resolve_path(config["paths"]["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)

    dataset_hash, dataset_counts = dataset_fingerprint(data_yaml)
    dataset_info = {
        "data_yaml": str(data_yaml),
        "fingerprint": dataset_hash,
        "counts": dataset_counts,
    }

    env = environment_record()
    print("=" * 70)
    print("SCIOBRAILLE V2 TRAINING PIPELINE INITIALIZED")
    print(f"Platform:        {env['platform']}")
    print(f"Python:          {env['python']}")
    print(f"PyTorch:         {env['pytorch']}")
    print(f"CUDA Available:  {env['cuda_available']} (Device: {env['cuda_device']}, VRAM: {env.get('cuda_vram_gb', 0)} GB)")
    print(f"Dataset YAML:    {data_yaml}")
    print(f"Dataset Counts:  {dataset_counts['images']} images (Train: 1440, Val: 165, Test: 179), {dataset_counts['labels']} labels")
    print(f"Production SHA:  {actual_prod_sha} (VERIFIED)")
    print("\n--- ESTIMATED TRAINING REQUIREMENTS ---")
    print("Batch size:      16 (approx 90 iterations per epoch)")
    print("Image resolution:640 x 640")
    print("Device:          NVIDIA GPU (CUDA)")
    print("Epochs:          Max 30 (patience: 7 for early stopping)")
    print("Est. Speed:      ~8-12 seconds / epoch (~4-6 minutes per candidate)")
    print("Total Est. Time: ~10-15 minutes for dual candidate runs (YOLOv8s + YOLO11s)")
    print("\n--- INTENDED EXPERIMENT CONFIGURATION ---")
    print("Candidate A:     YOLOv8s initialized from production Model B weights")
    print("Candidate B:     YOLO11s initialized from pretrained COCO weights")
    print("Augmentations:   Embossed-Braille safe photometric (no flipud, no fliplr)")
    print("Selection Rule:  Highest Master V2 validation mAP50-95")
    print("=" * 70, flush=True)

    global PHOTO_CONFIG
    PHOTO_CONFIG = config["photometric_augmentations"]

    # Evaluate production V1 on Master V2 validation and test splits as baseline
    print("\n[Baseline] Evaluating Production V1 on Master V2 validation split...", flush=True)
    v1_model = YOLO(str(prod_path))
    v1_val_metrics = evaluate_split(
        v1_model,
        data_yaml,
        split="val",
        output_dir=output_root / "v1_eval",
        conf=float(config["evaluation"]["validation_confidence"]),
        iou=float(config["evaluation"]["validation_iou"]),
        imgsz=int(config["training"]["imgsz"]),
    )
    v1_test_metrics = evaluate_split(
        v1_model,
        data_yaml,
        split="test",
        output_dir=output_root / "v1_eval",
        conf=float(config["evaluation"]["validation_confidence"]),
        iou=float(config["evaluation"]["validation_iou"]),
        imgsz=int(config["training"]["imgsz"]),
    )
    v1_latency = measure_inference_latency(v1_model, imgsz=int(config["training"]["imgsz"]))
    v1_bench = evaluate_frozen_benchmark(prod_path, benchmark_csv, inference_yaml)

    v1_comparison = {
        "path": str(prod_path),
        "sha256": actual_prod_sha,
        "size_bytes": prod_path.stat().st_size,
        "val_metrics": v1_val_metrics,
        "test_metrics": v1_test_metrics,
        "latency": v1_latency,
        "benchmark_metrics": v1_bench,
    }
    print(f"Production V1 Master V2 Val: mAP50-95={v1_val_metrics['map50_95']:.4f}, mAP50={v1_val_metrics['map50']:.4f}, Recall={v1_val_metrics['recall']:.4f}")
    print(f"Production V1 Master V2 Test: mAP50-95={v1_test_metrics['map50_95']:.4f}, mAP50={v1_test_metrics['map50']:.4f}, Recall={v1_test_metrics['recall']:.4f}", flush=True)

    # Train Candidates
    candidate_results = []
    for cand_key in ["candidate_a", "candidate_b"]:
        cand_cfg = config["candidates"][cand_key]
        res = train_candidate(cand_key, cand_cfg, config, data_yaml)
        candidate_results.append(res)

    # Selection: choose best candidate based on Master V2 validation mAP50-95
    candidate_results.sort(
        key=lambda c: (
            c["validation_metrics"]["map50_95"],
            c["validation_metrics"]["map50"],
            c["validation_metrics"]["recall"],
            -c["latency"]["average_latency_ms"],
        ),
        reverse=True,
    )
    selected = candidate_results[0]
    print(f"\n>>> SELECTION WINNER: {selected['name']} ({selected['arch']}) with val mAP50-95 = {selected['validation_metrics']['map50_95']:.4f} <<<", flush=True)

    # Internal test split evaluation (performed strictly POST-selection to prevent tuning leakage)
    for c in candidate_results:
        c_model = YOLO(c["best_checkpoint"])
        c["test_metrics"] = evaluate_split(
            c_model,
            data_yaml,
            split="test",
            output_dir=Path(c["run_dir"]),
            conf=float(config["evaluation"]["validation_confidence"]),
            iou=float(config["evaluation"]["validation_iou"]),
            imgsz=int(config["training"]["imgsz"]),
        )
        c["benchmark_metrics"] = evaluate_frozen_benchmark(
            Path(c["best_checkpoint"]), benchmark_csv, inference_yaml
        )
        print(f"Post-Selection Test Split for {c['name']}: mAP50-95={c['test_metrics']['map50_95']:.4f}, mAP50={c['test_metrics']['map50']:.4f}, Recall={c['test_metrics']['recall']:.4f}")

    # Copy winning checkpoint to models/v2_master/best.pt
    winner_checkpoint = Path(selected["best_checkpoint"])
    final_best_pt = output_root / "best.pt"
    tmp_best_pt = output_root / "best.pt.tmp"
    shutil.copy2(winner_checkpoint, tmp_best_pt)
    if file_sha256(tmp_best_pt) != selected["best_checkpoint_sha256"]:
        raise RuntimeError("Copied V2 checkpoint failed SHA-256 verification!")
    os.replace(tmp_best_pt, final_best_pt)
    print(f"\nFinal V2 model deployed to: {final_best_pt} (SHA: {file_sha256(final_best_pt)})")

    # Verify production model SHA-256 has not been altered
    prod_sha_after = file_sha256(prod_path)
    if prod_sha_after != expected_prod_sha:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Production model was altered during training!\nExpected: {expected_prod_sha}\nActual:   {prod_sha_after}"
        )
    print("Safety Check PASSED: Production model unchanged.")

    # Create models/v2_master/evaluation.json
    evaluation_payload = {
        "status": "finalized",
        "selected_candidate": {
            "name": selected["name"],
            "arch": selected["arch"],
            "checkpoint_sha256": selected["best_checkpoint_sha256"],
            "model_path": str(final_best_pt),
            "validation_metrics": selected["validation_metrics"],
            "test_metrics": selected["test_metrics"],
            "latency": selected["latency"],
            "benchmark_metrics": selected["benchmark_metrics"],
        },
        "all_candidates": candidate_results,
        "v1_baseline_comparison": v1_comparison,
        "dataset": dataset_info,
        "environment": env,
        "training_config": config["training"],
    }
    (output_root / "evaluation.json").write_text(json.dumps(evaluation_payload, indent=2), encoding="utf-8")

    # Create models/v2_master/config.yaml
    safe_config = json.loads(json.dumps(evaluation_payload, default=str))
    (output_root / "config.yaml").write_text(yaml.safe_dump(safe_config, sort_keys=False), encoding="utf-8")

    # Create models/v2_master/README.md
    readme_content = f"""# Sciobraille V2 Master Model

## Selected Model Details
- **Architecture:** {selected['arch']}
- **Candidate Name:** `{selected['name']}`
- **Checkpoint SHA-256:** `{selected['best_checkpoint_sha256']}`
- **Classes:** 26 canonical classes (`0=a` through `25=z`)
- **Input Resolution:** 640 x 640
- **Model File:** `best.pt`

## Dataset Lineage
- **Dataset:** Master V2 (deduplicated across Prabh merged, Sangam, and Asmitha)
- **Train Images:** 1,440
- **Validation Images:** 165
- **Internal Test Images:** 179
- **Total Retained Images:** {dataset_counts['images']}
- **Total Bounding Boxes:** {dataset_counts['labels']}

## Performance Metrics
- **Validation mAP50-95:** {selected['validation_metrics']['map50_95']:.4f}
- **Validation mAP50:** {selected['validation_metrics']['map50']:.4f}
- **Validation Recall:** {selected['validation_metrics']['recall']:.4f}
- **Validation Precision:** {selected['validation_metrics']['precision']:.4f}
- **Internal Test mAP50-95:** {selected['test_metrics']['map50_95']:.4f}
- **Internal Test mAP50:** {selected['test_metrics']['map50']:.4f}
- **Inference Latency:** {selected['latency']['average_latency_ms']} ms (desktop GPU)
- **Physical Benchmark CER:** {selected['benchmark_metrics']['cer']:.4f} (regression check only)

## Verification
- Loaded and verified via Ultralytics YOLO.
- Production model `sciobraille-scanner/backend/model/best.pt` preserved with SHA-256 `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`.
"""
    (output_root / "README.md").write_text(readme_content, encoding="utf-8")

    # Generate all markdown reports
    generate_reports(config, dataset_info, env, candidate_results, selected, v1_comparison, output_root)

    print("\n=======================================================")
    print("V2 PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Selected Checkpoint: {final_best_pt}")
    print(f"Validation mAP50-95:  {selected['validation_metrics']['map50_95']:.4f}")
    print(f"Test mAP50-95:        {selected['test_metrics']['map50_95']:.4f}")
    print("=======================================================\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
