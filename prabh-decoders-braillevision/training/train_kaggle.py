# =============================================================================
# BrailleVision -- Kaggle Training Script (Multi-Dataset Merged)
#
# HOW TO USE:
#   1. Upload braille_merged.zip as a Kaggle Dataset named "braille-merged"
#   2. Create a new Kaggle Notebook
#   3. Add "braille-merged" as input data
#   4. Notebook Settings -> Accelerator = GPU T4 x2, Internet = ON
#   5. Paste this ENTIRE script into a single code cell
#   6. Change MODEL_VARIANT to "A" or "B" (one per account)
#   7. Run -> "Save & Run All (Commit)" for background execution
#
# Account A (SAFE) -> MODEL_VARIANT = "A"  yolov8n, 100 epochs, mild aug
# Account B (PUSH) -> MODEL_VARIANT = "B"  yolov8s, 150 epochs, heavy aug
# =============================================================================

MODEL_VARIANT = "A"      # <<< CHANGE THIS: "A" for Account 1, "B" for Account 2
INT8 = True              # int8 TFLite export (smallest/fastest for mobile)

# ---- CELL 1: install -------------------------------------------------------
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "-q", "install", "-U", "ultralytics"])
print("Ultralytics installed.")

# ---- CELL 2: dataset -------------------------------------------------------
import os, glob, shutil, yaml
from ultralytics import YOLO

print("=" * 60)
print(f"  BrailleVision Training — Variant {MODEL_VARIANT}")
print("=" * 60)

# --- Locate the merged dataset ---
# When you upload braille_merged.zip as "braille-merged" on Kaggle,
# it extracts to /kaggle/input/braille-merged/
KAGGLE_INPUT = "/kaggle/input/braille-merged"

# Check multiple possible paths (Kaggle sometimes nests folders)
POSSIBLE_YAMLS = [
    os.path.join(KAGGLE_INPUT, "data.yaml"),
    os.path.join(KAGGLE_INPUT, "braille_merged", "data.yaml"),
]

DATA_YAML_SRC = None
for p in POSSIBLE_YAMLS:
    if os.path.exists(p):
        DATA_YAML_SRC = p
        break

if DATA_YAML_SRC:
    print(f"\n✅ Found merged dataset: {DATA_YAML_SRC}")
    DATA_ROOT = os.path.dirname(DATA_YAML_SRC)

    # Read original config
    with open(DATA_YAML_SRC) as f:
        cfg = yaml.safe_load(f)

    # Rewrite path to point to the actual Kaggle location
    cfg["path"] = DATA_ROOT
    # Ensure train/val are relative paths
    cfg["train"] = "images/train"
    cfg["val"] = "images/val"

    # Write corrected data.yaml to /kaggle/working (writable)
    DATA_YAML = "/kaggle/working/data.yaml"
    with open(DATA_YAML, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

    print(f"  Corrected data.yaml -> {DATA_YAML}")
    print(f"  path: {cfg['path']}")
    print(f"  nc: {cfg.get('nc')}  names: {cfg.get('names')}")
else:
    # Fallback: download from Roboflow directly
    print("\n⚠️  Merged dataset not found. Downloading from Roboflow...")
    subprocess.run([sys.executable, "-m", "pip", "-q", "install", "roboflow"])
    from roboflow import Roboflow
    rf = Roboflow(api_key=os.environ.get("ROBOFLOW_API_KEY", "YOUR_ROBOFLOW_KEY"))
    project = rf.workspace("yapayzeka").project("braille-detection-vxtp1")
    dataset = project.version(1).download("yolov8")
    DATA_YAML = os.path.join(dataset.location, "data.yaml")
    DATA_ROOT = dataset.location
    print(f"  Roboflow dataset: {DATA_YAML}")

assert os.path.exists(DATA_YAML), f"ERROR: data.yaml not found at {DATA_YAML}"

# --- Verify dataset ---
with open(DATA_YAML) as f:
    d = yaml.safe_load(f)

train_dir = os.path.join(d["path"], d["train"])
val_dir = os.path.join(d["path"], d["val"])

print(f"\n=== Dataset Verification ===")
if os.path.isdir(train_dir):
    n_train = len([f for f in os.listdir(train_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))])
    print(f"  ✅ Train: {n_train} images in {train_dir}")
else:
    print(f"  ❌ Train dir not found: {train_dir}")

if os.path.isdir(val_dir):
    n_val = len([f for f in os.listdir(val_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))])
    print(f"  ✅ Val: {n_val} images in {val_dir}")
else:
    print(f"  ❌ Val dir not found: {val_dir}")

print(f"  Classes: {d.get('nc')} -> {d.get('names')}")

# ---- CELL 3: configure model -----------------------------------------------
# DotNeuralNet pretrained weights — a YOLOv8 model already trained on braille
# detection (64 dot-pattern classes). The backbone already knows what braille
# cells look like. Ultralytics automatically reinitializes the detection head
# from 64→26 classes while keeping the backbone features (transfer learning).
PRETRAINED = os.path.join(DATA_ROOT, "dotneural_pretrained.pt")
if not os.path.exists(PRETRAINED):
    # Also check Kaggle input root
    for candidate in [
        "/kaggle/input/braille-merged/dotneural_pretrained.pt",
        os.path.join(KAGGLE_INPUT, "dotneural_pretrained.pt"),
    ]:
        if os.path.exists(candidate):
            PRETRAINED = candidate
            break

HAS_PRETRAINED = os.path.exists(PRETRAINED)

if MODEL_VARIANT == "A":
    if HAS_PRETRAINED:
        # SAFE: Use braille-pretrained backbone (massive head start)
        BASE = PRETRAINED
        print(f"\n  🚀 Using DotNeuralNet pretrained warm-start: {BASE}")
        print(f"     Backbone already knows braille → head retrained for a-z")
    else:
        BASE = "yolov8n.pt"
        print(f"\n  ⚠️  DotNeuralNet weights not found, using COCO-pretrained: {BASE}")
    IMGSZ = 640
    EPOCHS = 100
    BATCH = 16
    LR0 = 0.01
    AUG = dict(
        degrees=5,
        translate=0.05,
        scale=0.3,
        hsv_v=0.3,
        mosaic=1.0,
    )
else:  # "B"
    # PUSH: YOLOv8 small from COCO — more capacity, heavier augmentation
    # Intentionally NOT using DotNeuralNet here so we compare two approaches
    BASE = "yolov8s.pt"
    IMGSZ = 640
    EPOCHS = 150
    BATCH = 16
    LR0 = 0.01
    AUG = dict(
        degrees=10,
        translate=0.10,
        scale=0.5,
        shear=3,
        perspective=0.0005,
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.5,
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.1,
    )

print(f"\n=== Training Config ===")
print(f"  Variant:    {MODEL_VARIANT}")
print(f"  Base model: {BASE}")
print(f"  Image size: {IMGSZ}")
print(f"  Epochs:     {EPOCHS}")
print(f"  Batch:      {BATCH}")
print(f"  LR:         {LR0}")
print(f"  Int8 TFLite:{INT8}")

# ---- CELL 4: train ---------------------------------------------------------
print(f"\n{'='*60}")
print(f"  STARTING TRAINING — Variant {MODEL_VARIANT}")
print(f"{'='*60}\n")

model = YOLO(BASE)
results = model.train(
    data=DATA_YAML,
    imgsz=IMGSZ,
    epochs=EPOCHS,
    batch=BATCH,
    patience=30,           # early stopping if no improvement for 30 epochs
    device=0,
    cache=True,            # cache images in RAM for speed
    optimizer="AdamW",
    lr0=LR0,
    lrf=0.01,              # cosine decay: final LR = lr0 * 0.01
    warmup_epochs=5,
    project="braille",
    name=f"variant_{MODEL_VARIANT}",
    exist_ok=True,
    plots=True,            # save confusion matrix, results, etc.
    save=True,
    save_period=25,        # checkpoint every 25 epochs (safety net)
    verbose=True,
    **AUG
)

# ---- CELL 5: validate ------------------------------------------------------
print(f"\n{'='*60}")
print(f"  VALIDATION RESULTS")
print(f"{'='*60}")

m = model.val()
map50 = float(m.box.map50)
map50_95 = float(m.box.map)
precision = float(m.box.mp)
recall = float(m.box.mr)

print(f"  mAP@50:     {map50:.4f}")
print(f"  mAP@50-95:  {map50_95:.4f}")
print(f"  Precision:  {precision:.4f}")
print(f"  Recall:     {recall:.4f}")

# ---- CELL 6: save everything to /kaggle/working ----------------------------
print(f"\n=== Saving outputs ===")
OUT = "/kaggle/working"

# Save best/last weights
best_pt = f"braille/variant_{MODEL_VARIANT}/weights/best.pt"
last_pt = f"braille/variant_{MODEL_VARIANT}/weights/last.pt"

for src_path in [best_pt, last_pt]:
    if os.path.exists(src_path):
        fname = os.path.basename(src_path).replace('.pt', f'_{MODEL_VARIANT}.pt')
        dst = os.path.join(OUT, fname)
        shutil.copy(src_path, dst)
        print(f"  ✅ {fname} ({os.path.getsize(dst)//1024//1024}MB)")

# Save training plots
plots_saved = []
for pattern in ["results.png", "confusion_matrix.png", "confusion_matrix_normalized.png",
                "F1_curve.png", "P_curve.png", "R_curve.png", "PR_curve.png",
                "labels.jpg", "labels_correlogram.jpg"]:
    matches = glob.glob(f"braille/variant_{MODEL_VARIANT}/**/{pattern}", recursive=True)
    if not matches:
        matches = glob.glob(f"braille/variant_{MODEL_VARIANT}/{pattern}")
    for f_path in matches:
        ext = os.path.splitext(pattern)[1]
        dst_name = pattern.replace(ext, f'_{MODEL_VARIANT}{ext}')
        shutil.copy(f_path, os.path.join(OUT, dst_name))
        plots_saved.append(dst_name)
        print(f"  ✅ {dst_name}")

# Save metrics as text file for easy reference
with open(os.path.join(OUT, f"metrics_{MODEL_VARIANT}.txt"), "w") as f:
    f.write(f"BrailleVision — Variant {MODEL_VARIANT}\n")
    f.write(f"{'='*40}\n")
    f.write(f"Base model: {BASE}\n")
    f.write(f"Epochs: {EPOCHS}\n")
    f.write(f"Image size: {IMGSZ}\n")
    f.write(f"Batch: {BATCH}\n")
    f.write(f"mAP@50:    {map50:.4f}\n")
    f.write(f"mAP@50-95: {map50_95:.4f}\n")
    f.write(f"Precision: {precision:.4f}\n")
    f.write(f"Recall:    {recall:.4f}\n")
print(f"  ✅ metrics_{MODEL_VARIANT}.txt")

# ---- CELL 7: export TFLite for mobile app ----------------------------------
print(f"\n=== Exporting TFLite ===")
try:
    YOLO(best_pt).export(
        format="tflite",
        int8=INT8,
        half=(not INT8),
        data=DATA_YAML,
        imgsz=IMGSZ
    )
    tfls = sorted(glob.glob("**/*.tflite", recursive=True), key=os.path.getmtime)
    if tfls:
        shutil.copy(tfls[-1], os.path.join(OUT, f"best_{MODEL_VARIANT}.tflite"))
        print(f"  ✅ best_{MODEL_VARIANT}.tflite")
    else:
        print("  ⚠️  No .tflite produced")
except Exception as e:
    print(f"  ⚠️  TFLite export failed: {e}")
    print("     (This is OK — you still have best.pt for inference)")

# ---- DONE -------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"  ✅ TRAINING COMPLETE — Variant {MODEL_VARIANT}")
print(f"{'='*60}")
print(f"\n  Results in /kaggle/working (Output tab):")
print(f"    • best_{MODEL_VARIANT}.pt      — trained weights")
print(f"    • best_{MODEL_VARIANT}.tflite  — mobile export")
print(f"    • metrics_{MODEL_VARIANT}.txt  — final metrics")
print(f"    • results_{MODEL_VARIANT}.png  — training curves")
print(f"    • confusion_matrix_{MODEL_VARIANT}.png")
print(f"\n  mAP@50: {map50:.4f}  |  mAP@50-95: {map50_95:.4f}")
print(f"  Precision: {precision:.4f}  |  Recall: {recall:.4f}")
print(f"\n  Next: download best_{MODEL_VARIANT}.pt -> place in model/best.pt")
print(f"        then run: python inference.py --source sample_inputs/ --weights model/best.pt")
print(f"{'='*60}")
