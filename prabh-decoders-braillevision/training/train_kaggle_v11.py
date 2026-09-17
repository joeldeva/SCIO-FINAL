# =============================================================================
# BrailleVision -- Kaggle Training Script — Model C (YOLOv11n)
#
# HOW TO USE:
#   1. Use the SAME "braille-merged" dataset already uploaded on Kaggle
#   2. Create a new Kaggle Notebook
#   3. Add "braille-merged" as input data
#   4. Notebook Settings -> Accelerator = GPU T4 x2, Internet = ON
#   5. Paste this ENTIRE script into a single code cell
#   6. Run -> "Save & Run All (Commit)" for background execution
#
# Model C: YOLOv11n (latest generation, ~5MB, fastest inference)
# =============================================================================

MODEL_VARIANT = "C"
INT8 = True

# ---- CELL 1: install -------------------------------------------------------
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "-q", "install", "-U", "ultralytics"])
print("Ultralytics installed.")

# ---- CELL 2: dataset -------------------------------------------------------
import os, glob, shutil, yaml
from ultralytics import YOLO

print("=" * 60)
print(f"  BrailleVision Training — Model C (YOLOv11n)")
print("=" * 60)

# --- Locate the merged dataset ---
KAGGLE_INPUT = "/kaggle/input/braille-merged"

POSSIBLE_YAMLS = [
    os.path.join(KAGGLE_INPUT, "data.yaml"),
    os.path.join(KAGGLE_INPUT, "braille_merged", "data.yaml"),
]

DATA_YAML_SRC = None
DATA_ROOT = None
for p in POSSIBLE_YAMLS:
    if os.path.exists(p):
        DATA_YAML_SRC = p
        DATA_ROOT = os.path.dirname(p)
        break

if DATA_YAML_SRC:
    print(f"\n✅ Found merged dataset: {DATA_YAML_SRC}")

    with open(DATA_YAML_SRC) as f:
        cfg = yaml.safe_load(f)

    cfg["path"] = DATA_ROOT
    cfg["train"] = "images/train"
    cfg["val"] = "images/val"

    DATA_YAML = "/kaggle/working/data.yaml"
    with open(DATA_YAML, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

    print(f"  Corrected data.yaml -> {DATA_YAML}")
    print(f"  path: {cfg['path']}")
    print(f"  nc: {cfg.get('nc')}  names: {cfg.get('names')}")
else:
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
    print(f"  ✅ Train: {n_train} images")
else:
    print(f"  ❌ Train dir not found: {train_dir}")

if os.path.isdir(val_dir):
    n_val = len([f for f in os.listdir(val_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))])
    print(f"  ✅ Val: {n_val} images")
else:
    print(f"  ❌ Val dir not found: {val_dir}")

print(f"  Classes: {d.get('nc')} -> {d.get('names')}")

# ---- CELL 3: configure model -----------------------------------------------
# YOLOv11n — latest generation nano model
# Smaller than v8n, better accuracy per parameter, fastest inference
BASE = "yolo11n.pt"
IMGSZ = 640
EPOCHS = 120
BATCH = 16
LR0 = 0.01
AUG = dict(
    degrees=7,
    translate=0.08,
    scale=0.4,
    hsv_v=0.4,
    hsv_s=0.3,
    mosaic=1.0,
    mixup=0.05,
)

print(f"\n=== Training Config ===")
print(f"  Model:      YOLOv11n (latest gen nano)")
print(f"  Base:       {BASE}")
print(f"  Image size: {IMGSZ}")
print(f"  Epochs:     {EPOCHS}")
print(f"  Batch:      {BATCH}")
print(f"  LR:         {LR0}")

# ---- CELL 4: train ---------------------------------------------------------
print(f"\n{'='*60}")
print(f"  STARTING TRAINING — Model C (YOLOv11n)")
print(f"{'='*60}\n")

model = YOLO(BASE)
results = model.train(
    data=DATA_YAML,
    imgsz=IMGSZ,
    epochs=EPOCHS,
    batch=BATCH,
    patience=30,
    device=0,
    cache=True,
    optimizer="AdamW",
    lr0=LR0,
    lrf=0.01,
    warmup_epochs=5,
    project="braille",
    name=f"variant_{MODEL_VARIANT}",
    exist_ok=True,
    plots=True,
    save=True,
    save_period=25,
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

best_pt = f"braille/variant_{MODEL_VARIANT}/weights/best.pt"
last_pt = f"braille/variant_{MODEL_VARIANT}/weights/last.pt"

for src_path in [best_pt, last_pt]:
    if os.path.exists(src_path):
        fname = os.path.basename(src_path).replace('.pt', f'_{MODEL_VARIANT}.pt')
        dst = os.path.join(OUT, fname)
        shutil.copy(src_path, dst)
        sz = os.path.getsize(dst) / 1024 / 1024
        print(f"  ✅ {fname} ({sz:.1f}MB)")

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

with open(os.path.join(OUT, f"metrics_{MODEL_VARIANT}.txt"), "w") as f:
    f.write(f"BrailleVision — Model C (YOLOv11n)\n")
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
print(f"  ✅ TRAINING COMPLETE — Model C (YOLOv11n)")
print(f"{'='*60}")
print(f"\n  Results in /kaggle/working (Output tab):")
print(f"    • best_{MODEL_VARIANT}.pt      — trained weights")
print(f"    • best_{MODEL_VARIANT}.tflite  — mobile export")
print(f"    • metrics_{MODEL_VARIANT}.txt  — final metrics")
print(f"    • results_{MODEL_VARIANT}.png  — training curves")
print(f"    • confusion_matrix_{MODEL_VARIANT}.png")
print(f"\n  mAP@50: {map50:.4f}  |  mAP@50-95: {map50_95:.4f}")
print(f"  Precision: {precision:.4f}  |  Recall: {recall:.4f}")
print(f"\n  Compare with Model A (93.28%) and Model B (93.15%)")
print(f"{'='*60}")
