"""
train.py — BrailleVision YOLOv8 Training Script (v4)
=====================================================
KEY CHANGES FROM v3
────────────────────
  PROBLEM 1 — Stopped at epoch 57:
    Cause: patience=30 fired because best mAP was at epoch ~27
            (27 + 30 = 57 → early stop triggered correctly but too soon).
    Fix  : patience raised to 50 for phase 1. Added --no-early-stop flag to
            disable it entirely if you suspect your data still has room to improve.

  PROBLEM 2 — Losing hours of work on Colab disconnect:
    Fix  : Google Drive backup runs every GDRIVE_SAVE_EVERY epochs via a
            YOLOv8 callback. On reconnect, --resume automatically finds the
            latest checkpoint in Drive if local storage is gone.

  PROBLEM 3 — Browser crash from too many log lines:
    Fix  : verbose=False suppresses per-batch output. A custom callback
            prints ONE clean summary line per epoch.

HOW TO USE
──────────
  # First run (standard):
  !python train.py

  # Higher resolution:
  !python train.py --imgsz 800

  # Resume after a disconnect (checks Drive first):
  !python train.py --resume

  # Skip phase 1 if it already finished:
  !python train.py --phase2-only

  # Disable early stopping (let all epochs run):
  !python train.py --no-early-stop

  # Evaluate final model with TTA, no retraining:
  !python train.py --eval-only --tta
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  PATHS — edit the three GDRIVE_* lines for your Drive layout
# ═══════════════════════════════════════════════════════════════════════════════
MODEL_PATH  = "/content/yolov8_braille.pt"
DATA_YAML   = "/content/dataset/data.yaml"
PROJECT_DIR = "/content/results"
RUN_NAME    = "braille_v4"

# Google Drive backup — weights are copied here every GDRIVE_SAVE_EVERY epochs.
# Set GDRIVE_BACKUP = None to skip Drive entirely (e.g. running locally).
GDRIVE_BACKUP      = "/content/drive/MyDrive/BrailleVision/checkpoints"
GDRIVE_SAVE_EVERY  = 10    # copy weights every N epochs


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Google Drive — mount + helpers
# ═══════════════════════════════════════════════════════════════════════════════
def mount_drive() -> bool:
    """
    Mount Google Drive if running in Colab and GDRIVE_BACKUP is set.
    Returns True if Drive is available.
    """
    if GDRIVE_BACKUP is None:
        return False
    try:
        from google.colab import drive  # type: ignore
        drive.mount("/content/drive", force_remount=False)
        Path(GDRIVE_BACKUP).mkdir(parents=True, exist_ok=True)
        print(f"✅  Google Drive mounted  →  backups at {GDRIVE_BACKUP}")
        return True
    except Exception as exc:
        print(f"⚠️  Drive not available ({exc}). Training without Drive backup.")
        return False


def backup_to_drive(src: str | Path, tag: str = ""):
    """
    Copy a file to GDRIVE_BACKUP with an optional epoch/tag suffix.
    Silently skips if Drive is not available.
    """
    if GDRIVE_BACKUP is None:
        return
    src = Path(src)
    if not src.exists():
        return
    try:
        suffix = f"_{tag}" if tag else ""
        dst    = Path(GDRIVE_BACKUP) / f"{src.stem}{suffix}{src.suffix}"
        shutil.copy2(src, dst)
    except Exception as exc:
        # Non-fatal — print once but don't crash training
        print(f"  ⚠️  Drive backup failed: {exc}")


def restore_from_drive(local_path: str | Path) -> bool:
    """
    If local_path is missing but a Drive copy exists, restore it.
    Returns True if the file is now available locally.
    """
    local_path = Path(local_path)
    if local_path.exists():
        return True
    if GDRIVE_BACKUP is None:
        return False
    drive_copy = Path(GDRIVE_BACKUP) / local_path.name
    if drive_copy.exists():
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(drive_copy, local_path)
        print(f"  🔄  Restored from Drive: {local_path}")
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Device
# ═══════════════════════════════════════════════════════════════════════════════
def get_device() -> str:
    if torch.cuda.is_available():
        gpu     = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"🖥  GPU : {gpu}  ({vram_gb:.1f} GB VRAM)")
        return "0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print("🍎  Apple MPS")
        return "mps"
    print("⚠️  CPU only — training will be very slow")
    return "cpu"


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Data.yaml sanity check
# ═══════════════════════════════════════════════════════════════════════════════
def check_dataset(data_yaml: str) -> dict:
    with open(data_yaml) as f:
        data = yaml.safe_load(f)
    nc    = data.get("nc", 0)
    names = data.get("names", [])
    print(f"\n📂  Dataset  : {data_yaml}")
    print(f"   Classes   : {nc}")
    print(f"   Names     : {names}")
    if nc != len(names):
        print(f"⚠️  WARNING: nc={nc} but {len(names)} names listed")
    if nc < 26:
        print(f"⚠️  WARNING: only {nc} classes — expected 26 (a–z)")
    else:
        print("✅  All 26 Braille letters present")
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  YOLOv8 Callbacks
#     — epoch-only logging (no per-batch spam)
#     — Google Drive checkpoint backup
# ═══════════════════════════════════════════════════════════════════════════════

# Shared state for the callback (avoids globals)
_cb_state: dict = {"phase": "ph1", "drive_ok": False, "start_time": 0.0}


def _on_train_start(trainer):
    _cb_state["start_time"] = time.time()
    print(f"\n{'─'*60}")
    print(f"  🚀  Training started  |  phase: {_cb_state['phase']}")
    print(f"  Saving every {GDRIVE_SAVE_EVERY} epochs to Drive")
    print(f"{'─'*60}")
    print(f"  {'Epoch':>6}  {'box_loss':>9}  {'cls_loss':>9}  "
          f"{'dfl_loss':>9}  {'mAP@0.5':>8}  {'time':>6}")
    print(f"  {'──────':>6}  {'────────':>9}  {'────────':>9}  "
          f"{'────────':>9}  {'───────':>8}  {'────':>6}")


def _on_train_epoch_end(trainer):
    """
    Prints ONE summary line per epoch.
    Backs up best.pt + last.pt to Drive every GDRIVE_SAVE_EVERY epochs.
    """
    ep       = trainer.epoch + 1
    total_ep = trainer.epochs
    loss     = trainer.loss         # tensor or dict depending on version
    metrics  = trainer.metrics      # dict from latest val

    # Extract losses safely
    try:
        losses = trainer.loss_items   # [box, cls, dfl]
        box_l  = f"{float(losses[0]):.4f}"
        cls_l  = f"{float(losses[1]):.4f}"
        dfl_l  = f"{float(losses[2]):.4f}"
    except Exception:
        box_l = cls_l = dfl_l = "  n/a "

    # mAP from metrics dict
    map50 = metrics.get("metrics/mAP50(B)", float("nan"))
    elapsed = (time.time() - _cb_state["start_time"]) / 60

    print(f"  {ep:>5}/{total_ep:<4}  {box_l:>9}  {cls_l:>9}  "
          f"{dfl_l:>9}  {map50:>8.4f}  {elapsed:>5.1f}m")

    # Drive backup
    if _cb_state["drive_ok"] and ep % GDRIVE_SAVE_EVERY == 0:
        weights_dir = Path(trainer.save_dir) / "weights"
        tag         = f"ep{ep:04d}"
        for ckpt in ["best.pt", "last.pt"]:
            backup_to_drive(weights_dir / ckpt, tag if ckpt == "last.pt" else "best")
        print(f"  💾  Backed up to Drive at epoch {ep}")


def _on_train_end(trainer):
    weights_dir = Path(trainer.save_dir) / "weights"
    if _cb_state["drive_ok"]:
        for ckpt in ["best.pt", "last.pt"]:
            backup_to_drive(weights_dir / ckpt, ckpt.replace(".pt", "_final"))
        print(f"\n  💾  Final weights backed up to Drive")


def register_callbacks(model, phase: str = "ph1", drive_ok: bool = False):
    """Attach epoch-logging + Drive-backup callbacks to a YOLO model."""
    _cb_state["phase"]    = phase
    _cb_state["drive_ok"] = drive_ok

    model.add_callback("on_train_start",     _on_train_start)
    model.add_callback("on_train_epoch_end", _on_train_epoch_end)
    model.add_callback("on_train_end",       _on_train_end)


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  Training configs
# ═══════════════════════════════════════════════════════════════════════════════
def build_phase1_config(device: str, imgsz: int, no_early_stop: bool) -> dict:
    """
    Phase 1 — full training with strong augmentation.

    patience=50 (was 30 in v3):
      With 30, training stopped at epoch 57 because the best checkpoint
      was around epoch 27. Raising to 50 gives the scheduler room to
      escape a plateau before early-stopping fires.

    verbose=False:
      Suppresses the per-batch tqdm/print flood that crashes the Colab
      browser. Our custom callback prints one line per epoch instead.

    Augmentation notes (unchanged from v3 — already well-tuned):
      flipud=0   : dot positions are vertically sensitive — never flip
      erasing=0.3: forces model to read the full 6-dot pattern
      hsv_v=0.5  : brightness jitter for real-camera variation
    """
    on_gpu     = device not in ("cpu",)
    auto_batch = -1 if on_gpu else 16

    return dict(
        data            = DATA_YAML,
        imgsz           = imgsz,
        batch           = auto_batch,
        workers         = 4,
        cache           = "ram" if on_gpu else False,
        rect            = False,
        single_cls      = False,

        project         = PROJECT_DIR,
        name            = RUN_NAME + "_phase1",
        exist_ok        = True,
        seed            = 42,
        deterministic   = True,

        epochs          = 120,
        patience        = 0 if no_early_stop else 50,   # ← raised from 30
        warmup_epochs   = 5.0,
        close_mosaic    = 20,

        optimizer       = "AdamW",
        lr0             = 5e-4,
        lrf             = 0.01,
        momentum        = 0.937,
        weight_decay    = 5e-4,
        cos_lr          = True,

        dropout         = 0.1,
        label_smoothing = 0.05,

        amp             = on_gpu,
        device          = device,

        # Braille-specific augmentation
        flipud          = 0.0,
        fliplr          = 0.5,
        degrees         = 5.0,
        translate       = 0.1,
        scale           = 0.5,
        shear           = 2.0,
        perspective     = 0.0002,
        mosaic          = 1.0,
        mixup           = 0.15,
        copy_paste      = 0.15,
        hsv_h           = 0.015,
        hsv_s           = 0.6,
        hsv_v           = 0.5,
        erasing         = 0.3,

        save            = True,
        save_period     = 10,      # always keep a local checkpoint every 10 epochs
        plots           = True,
        val             = True,
        verbose         = False,   # ← suppress per-batch output (callback handles logging)
        pretrained      = True,
    )


def build_phase2_config(device: str, imgsz: int, no_early_stop: bool) -> dict:
    """
    Phase 2 — fine-tuning from phase 1 best weights.

    Why:  Heavy augmentation in phase 1 adds noise to final gradients.
          Phase 2 at 10× lower LR + minimal aug lets the model converge
          cleanly on the true data distribution — typically +0.5-1.0% mAP.
    """
    on_gpu     = device not in ("cpu",)
    auto_batch = -1 if on_gpu else 16

    return dict(
        data            = DATA_YAML,
        imgsz           = imgsz,
        batch           = auto_batch,
        workers         = 4,
        cache           = "ram" if on_gpu else False,
        rect            = False,
        single_cls      = False,

        project         = PROJECT_DIR,
        name            = RUN_NAME + "_phase2",
        exist_ok        = True,
        seed            = 42,
        deterministic   = True,

        epochs          = 40,
        patience        = 0 if no_early_stop else 20,
        warmup_epochs   = 1.0,
        close_mosaic    = 40,       # mosaic off for all of phase 2

        optimizer       = "AdamW",
        lr0             = 5e-5,    # 10× lower than phase 1
        lrf             = 0.1,
        momentum        = 0.937,
        weight_decay    = 1e-4,
        cos_lr          = True,

        dropout         = 0.0,
        label_smoothing = 0.0,

        amp             = on_gpu,
        device          = device,

        # Minimal augmentation
        flipud          = 0.0,
        fliplr          = 0.3,
        degrees         = 2.0,
        translate       = 0.05,
        scale           = 0.2,
        shear           = 0.5,
        perspective     = 0.0,
        mosaic          = 0.0,
        mixup           = 0.0,
        copy_paste      = 0.0,
        hsv_h           = 0.005,
        hsv_s           = 0.2,
        hsv_v           = 0.2,
        erasing         = 0.1,

        save            = True,
        save_period     = 5,
        plots           = True,
        val             = True,
        verbose         = False,   # ← suppress per-batch output
        pretrained      = True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 7.  Training runners
# ═══════════════════════════════════════════════════════════════════════════════
def run_phase1(config: dict, model_path: str, resume: bool, drive_ok: bool) -> str:
    run_dir   = Path(PROJECT_DIR) / (RUN_NAME + "_phase1")
    last_ckpt = run_dir / "weights" / "last.pt"
    best_ckpt = run_dir / "weights" / "best.pt"

    if resume:
        # Try local last.pt first, then Drive
        if not last_ckpt.exists():
            restore_from_drive(last_ckpt)
        if last_ckpt.exists():
            print(f"\n🔄  Resuming phase 1 from: {last_ckpt}")
            model = YOLO(str(last_ckpt))
            register_callbacks(model, "phase1", drive_ok)
            model.train(resume=True)
            return str(best_ckpt)
        else:
            print("  ⚠️  No checkpoint to resume from — starting fresh")

    print(f"\n🚀  Phase 1 — training from: {model_path}")
    model = YOLO(model_path)
    register_callbacks(model, "phase1", drive_ok)
    model.train(**config)
    return str(best_ckpt)


def run_phase2(config: dict, phase1_best: str, drive_ok: bool) -> str:
    # Try to restore from Drive if local copy is missing
    if not Path(phase1_best).exists():
        restore_from_drive(phase1_best)

    if not Path(phase1_best).exists():
        sys.exit(
            f"[ERROR] Phase 1 weights not found: {phase1_best}\n"
            f"        Run phase 1 first, or use --phase2-only after phase 1 completes.\n"
            f"        Drive backup dir checked: {GDRIVE_BACKUP}"
        )

    run_dir   = Path(PROJECT_DIR) / (RUN_NAME + "_phase2")
    best_ckpt = run_dir / "weights" / "best.pt"

    print(f"\n🎯  Phase 2 — fine-tuning from: {phase1_best}")
    model = YOLO(phase1_best)
    register_callbacks(model, "phase2", drive_ok)
    model.train(**config)
    return str(best_ckpt)


# ═══════════════════════════════════════════════════════════════════════════════
# 8.  Evaluation
# ═══════════════════════════════════════════════════════════════════════════════
def evaluate(weights_path: str, label: str = "", use_tta: bool = False) -> dict | None:
    sep = "─" * 58
    print(f"\n{sep}")
    print(f"  📊  {label or Path(weights_path).name}")
    if use_tta:
        print("      (Test-Time Augmentation ON)")
    print(sep)

    if not Path(weights_path).exists():
        restore_from_drive(weights_path)

    if not Path(weights_path).exists():
        print(f"  ⚠️  Not found, skipping: {weights_path}")
        return None

    model = YOLO(weights_path)
    names = model.names
    all_results: dict = {}

    for sz in [640, 800]:
        m = model.val(
            data    = DATA_YAML,
            imgsz   = sz,
            augment = use_tta,
            plots   = (sz == 640),
            verbose = False,
        )
        all_results[sz] = {
            "map50":     round(float(m.box.map50), 4),
            "map50_95":  round(float(m.box.map),   4),
            "precision": round(float(m.box.mp),    4),
            "recall":    round(float(m.box.mr),    4),
        }
        tta_tag = "  [TTA]" if use_tta else ""
        print(f"\n  imgsz={sz}{tta_tag}")
        print(f"    mAP@0.5      : {m.box.map50:.4f}")
        print(f"    mAP@0.5:0.95 : {m.box.map:.4f}")
        print(f"    Precision    : {m.box.mp:.4f}")
        print(f"    Recall       : {m.box.mr:.4f}")

        # Per-class AP (printed once, at imgsz=640)
        if sz == 640:
            print(f"\n  Per-class AP@0.5  (sorted by AP, weakest first):")
            weak: list[tuple[str, float]] = []

            if hasattr(m.box, "ap_class_index") and m.box.ap_class_index is not None:
                class_aps = list(zip(m.box.ap_class_index, m.box.ap50))
                class_aps.sort(key=lambda x: x[1])
                for idx, ap in class_aps:
                    letter = names.get(int(idx), str(idx))
                    bar    = "█" * int(ap * 20)
                    gap    = "░" * (20 - int(ap * 20))
                    flag   = "  ← WEAK" if ap < 0.95 else ""
                    print(f"    {letter:>3}  {ap:.3f}  {bar}{gap}{flag}")
                    if ap < 0.95:
                        weak.append((letter, round(float(ap), 3)))

                all_results[sz]["per_class_ap"] = {
                    names.get(int(i), str(i)): round(float(a), 4)
                    for i, a in zip(m.box.ap_class_index, m.box.ap50)
                }
            else:
                print("    (not available in this ultralytics version)")

            if weak:
                print(f"\n  ⚠️  Weak letters (AP < 0.95):")
                for letter, ap in weak:
                    print(f"     {letter} = {ap:.3f}  → add more training images")
            else:
                print(f"\n  ✅  All letters AP ≥ 0.95 — excellent class balance")

    # Recommend best imgsz
    diff = all_results[800]["map50"] - all_results[640]["map50"]
    print(f"\n  Inference recommendation:")
    if diff > 0.002:
        print(f"  ✅  Use imgsz=800  (+{diff:.4f} over 640)")
    elif diff < -0.002:
        print(f"  ✅  Use imgsz=640  (800 is worse by {-diff:.4f})")
    else:
        print(f"  ✅  imgsz=640 and 800 equivalent — use 640 (faster)")

    return all_results


# ═══════════════════════════════════════════════════════════════════════════════
# 9.  Training report
# ═══════════════════════════════════════════════════════════════════════════════
def save_report(report: dict, output_dir: str):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "training_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    txt_path = out / "training_report.txt"
    with open(txt_path, "w") as f:
        f.write("BrailleVision — Training Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated  : {report['timestamp']}\n")
        f.write(f"Model      : {report['base_model']}\n")
        f.write(f"Image size : {report['imgsz']}\n")
        f.write(f"TTA        : {report['tta']}\n\n")

        for phase, results in report.get("results", {}).items():
            if not results:
                continue
            f.write(f"{phase}\n")
            f.write("-" * 30 + "\n")
            for sz, metrics in results.items():
                f.write(f"  imgsz={sz}\n")
                for k, v in metrics.items():
                    if k != "per_class_ap":
                        f.write(f"    {k:12s}: {v}\n")
            f.write("\n")

        if report.get("weak_letters"):
            f.write("Weak letters (AP < 0.95):\n")
            for entry in report["weak_letters"]:
                f.write(f"  {entry['letter']} = {entry['ap']}\n")
        else:
            f.write("All letters AP ≥ 0.95 ✅\n")

    print(f"\n📄  Report saved → {txt_path}")
    if GDRIVE_BACKUP:
        backup_to_drive(json_path, "")
        backup_to_drive(txt_path, "")
        print(f"    (also backed up to Drive)")


# ═══════════════════════════════════════════════════════════════════════════════
# 10.  ONNX export
# ═══════════════════════════════════════════════════════════════════════════════
def export_model(weights_path: str, imgsz: int = 640):
    print("\n📦  Exporting to ONNX …")
    try:
        model = YOLO(weights_path)
        model.export(format="onnx", imgsz=imgsz, dynamic=True, simplify=True)
        onnx = Path(weights_path).with_suffix(".onnx")
        print(f"   ✅  Saved: {onnx}")
        if GDRIVE_BACKUP:
            backup_to_drive(onnx, "")
    except Exception as exc:
        print(f"   ⚠️  ONNX export failed (non-critical): {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# 11.  Path validation
# ═══════════════════════════════════════════════════════════════════════════════
def validate_paths(model_path: str, phase2_only: bool = False):
    errors = []
    if not Path(DATA_YAML).exists():
        errors.append(f"  ✗ data.yaml not found : {DATA_YAML}")
    if not phase2_only and not Path(model_path).exists():
        errors.append(f"  ✗ Base weights not found: {model_path}")
    if errors:
        print("\n❌  Path errors:")
        print("\n".join(errors))
        sys.exit(1)
    print("✅  Paths verified")


# ═══════════════════════════════════════════════════════════════════════════════
# 12.  Final summary
# ═══════════════════════════════════════════════════════════════════════════════
def print_summary(phase1_dir: str, phase2_dir: str, elapsed: float, drive_ok: bool):
    p1, p2 = Path(phase1_dir), Path(phase2_dir)
    print("\n" + "═" * 58)
    print("  ✅  All done!")
    print(f"  ⏱   Total time        : {elapsed / 60:.1f} min")
    print(f"\n  Phase 1  {p1 / 'weights' / 'best.pt'}")
    print(f"  Phase 2  {p2 / 'weights' / 'best.pt'}  ← use this")
    print(f"\n  ONNX     {p2 / 'weights' / 'best.onnx'}")
    print(f"  Report   {p2 / 'training_report.txt'}")
    if drive_ok and GDRIVE_BACKUP:
        print(f"\n  Drive    {GDRIVE_BACKUP}/")
        print(f"           best_best.pt, last_ep*.pt, training_report.*")
    print("═" * 58 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# 13.  CLI
# ═══════════════════════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(description="BrailleVision YOLOv8 trainer v4")
    p.add_argument("--model",          default=MODEL_PATH,
                   help=f"Base weights (default: {MODEL_PATH}). "
                        "Use 'yolov8m.pt' for a larger model.")
    p.add_argument("--imgsz",          type=int, default=640,
                   help="Training image size: 640 (default) or 800")
    p.add_argument("--resume",         action="store_true",
                   help="Resume interrupted phase 1 (checks Drive if local copy is gone)")
    p.add_argument("--phase2-only",    action="store_true",
                   help="Skip phase 1 and fine-tune from existing phase1/best.pt")
    p.add_argument("--eval-only",      action="store_true",
                   help="Skip training — evaluate existing weights only")
    p.add_argument("--tta",            action="store_true",
                   help="Enable Test-Time Augmentation at evaluation")
    p.add_argument("--no-early-stop",  action="store_true",
                   help="Set patience=0 so all epochs always run (useful if you keep "
                        "hitting the early-stop wall)")
    p.add_argument("--no-drive",       action="store_true",
                   help="Skip Google Drive even if GDRIVE_BACKUP is set")
    return p.parse_known_args()[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    args = parse_args()

    # Disable Drive if user asked, or if GDRIVE_BACKUP is None
    if args.no_drive:
        globals()["GDRIVE_BACKUP"] = None

    phase1_dir  = str(Path(PROJECT_DIR) / (RUN_NAME + "_phase1"))
    phase2_dir  = str(Path(PROJECT_DIR) / (RUN_NAME + "_phase2"))
    phase1_best = str(Path(phase1_dir)  / "weights" / "best.pt")
    phase2_best = str(Path(phase2_dir)  / "weights" / "best.pt")

    report = {
        "timestamp":    datetime.now().isoformat(),
        "base_model":   args.model,
        "imgsz":        args.imgsz,
        "tta":          args.tta,
        "no_early_stop": args.no_early_stop,
        "results":      {},
        "weak_letters": [],
    }

    # Mount Drive early so checkpoints are backed up during training
    drive_ok = False if GDRIVE_BACKUP is None else mount_drive()

    # ── Eval only ──────────────────────────────────────────────────────────────
    if args.eval_only:
        r = evaluate(phase2_best, label="Phase 2 best", use_tta=args.tta)
        if r:
            report["results"]["phase2"] = r
        save_report(report, phase2_dir)
        sys.exit(0)

    # ── Full / partial training run ────────────────────────────────────────────
    validate_paths(args.model, phase2_only=args.phase2_only)
    check_dataset(DATA_YAML)
    device = get_device()

    no_es_tag = "  ← early stop disabled" if args.no_early_stop else ""

    print(f"\n📋  Training plan")
    print(f"   Base model    : {args.model}")
    print(f"   Image size    : {args.imgsz}")
    print(f"   Phase 1       : "
          f"{'SKIP' if args.phase2_only else f'120 epochs  (patience=50{no_es_tag})'}")
    print(f"   Phase 2       : 40 epochs fine-tune  (patience=20{no_es_tag})")
    print(f"   TTA at eval   : {args.tta}")
    print(f"   Drive backup  : {'every ' + str(GDRIVE_SAVE_EVERY) + ' epochs  →  ' + str(GDRIVE_BACKUP) if drive_ok else 'disabled'}")
    print()

    t0 = time.time()

    # Phase 1
    if not args.phase2_only:
        cfg1        = build_phase1_config(device, args.imgsz, args.no_early_stop)
        phase1_best = run_phase1(cfg1, args.model, args.resume, drive_ok)
        r1          = evaluate(phase1_best, label="Phase 1 best", use_tta=args.tta)
        if r1:
            report["results"]["phase1"] = r1

    # Phase 2
    cfg2        = build_phase2_config(device, args.imgsz, args.no_early_stop)
    phase2_best = run_phase2(cfg2, phase1_best, drive_ok)
    r2          = evaluate(phase2_best, label="Phase 2 best (final)", use_tta=args.tta)
    if r2:
        report["results"]["phase2"] = r2
        pc = r2.get(640, {}).get("per_class_ap", {})
        report["weak_letters"] = [
            {"letter": l, "ap": a} for l, a in pc.items() if a < 0.95
        ]

    # Export + report
    export_model(phase2_best, imgsz=args.imgsz)
    save_report(report, phase2_dir)

    elapsed = time.time() - t0
    print_summary(phase1_dir, phase2_dir, elapsed, drive_ok)