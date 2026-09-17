#!/usr/bin/env python3
"""
BrailleVision -- merge multiple Braille letter-detection datasets into ONE clean
YOLO dataset with a unified a-z class scheme.

What it does:
  * pulls each source (Roboflow download OR a local YOLO-format folder)
  * remaps every box's class to a canonical a-z index -- handles 'A', 'letter_a',
    'a_1', 'Letter_C', etc. -- and DROPS boxes that are not a single letter
    (dot, capital, TION, digits, punctuation), reporting what was dropped
  * pools all images, dedups by content hash, deterministic train/val split
  * writes images/{train,val}, labels/{train,val}, and a single data.yaml
  * prints per-class counts + per-source contribution + a dropped-class report

Why lowercase a-z: in Grade-1 Braille the cell for 'a' and 'A' is identical
(case is a separate prefix cell), so every letter is normalized to lowercase.

IMPORTANT: keep your OWN held-out rig photos OUT of this -- they are your TEST set.

Usage:
    # 1) set your API key
    export ROBOFLOW_API_KEY="your-private-key"
    # 2) run the merge
    python merge_datasets.py
    # 3) train on the result
    yolo detect train data=braille_merged/data.yaml model=yolov8n.pt imgsz=640
"""

import hashlib
import os
import random
import re
import shutil
import sys

import yaml

# ----------------------------- CONFIG --------------------------------------
ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "YOUR_ROBOFLOW_KEY")

# Each source is either:
#   {"tag": "...", "roboflow": (workspace, project, version)}  -- downloaded via API
#   {"tag": "...", "local": "path/to/yolo/dataset"}            -- already on disk
SOURCES = [
    # === Roboflow Universe datasets ===
    {"tag": "yapayzeka",  "roboflow": ("yapayzeka", "braille-detection-vxtp1", 1)},
    # braille-kp/braille-alphabet-v2 is a classification project (no bounding boxes)
    # so it can't be exported in YOLO detection format — removed.

    # === Converted local datasets ===
    # Angelina Braille Dataset (converted by converters/angelina_to_yolo.py)
    {"tag": "angelina",   "local": "datasets/angelina_yolo"},

    # Add your own labelled YOLO set here:
    # {"tag": "mine", "local": "datasets/my_captures"},
]

OUT_DIR = "braille_merged"
VAL_FRACTION = 0.15
SEED = 42
# ---------------------------------------------------------------------------

CANON = list("abcdefghijklmnopqrstuvwxyz")
CIDX = {c: i for i, c in enumerate(CANON)}
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def to_letter(raw):
    """Normalize a raw class name to a single a-z letter, or None if not a letter."""
    s = str(raw).strip().lower()
    if len(s) == 1 and s in CIDX:
        return s
    m = re.match(r'^(?:letter|char|class|alphabet|braille)?[_\-\s]*([a-z])(?:[_\-]?\d+)?$', s)
    return m.group(1) if m else None


def load_names(yaml_path):
    """Return {index:int -> name:str} from a YOLO data.yaml (list or dict names)."""
    with open(yaml_path) as f:
        d = yaml.safe_load(f)
    names = d.get("names")
    if isinstance(names, dict):
        return {int(k): v for k, v in names.items()}
    if isinstance(names, list):
        return {i: n for i, n in enumerate(names)}
    raise ValueError(f"Could not parse 'names' in {yaml_path}")


def find_split_dirs(root):
    """Yield (images_dir, labels_dir) for each split found under a dataset root."""
    pairs = []
    # Layout 1: <root>/<split>/images + <root>/<split>/labels  (Roboflow default)
    for split in ("train", "valid", "val", "test"):
        img = os.path.join(root, split, "images")
        lab = os.path.join(root, split, "labels")
        if os.path.isdir(img) and os.path.isdir(lab):
            pairs.append((img, lab))
    # Layout 2: <root>/images/<split> + <root>/labels/<split>  (common YOLO layout)
    if not pairs:
        for split in ("train", "valid", "val", "test"):
            img = os.path.join(root, "images", split)
            lab = os.path.join(root, "labels", split)
            if os.path.isdir(img) and os.path.isdir(lab):
                pairs.append((img, lab))
    # Layout 3: flat <root>/images + <root>/labels
    if not pairs:
        img, lab = os.path.join(root, "images"), os.path.join(root, "labels")
        if os.path.isdir(img) and os.path.isdir(lab):
            pairs.append((img, lab))
    return pairs


def download_roboflow(workspace, project, version, tag):
    """Download a dataset from Roboflow in YOLOv8 format."""
    from roboflow import Roboflow
    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    print(f"  downloading {workspace}/{project} v{version} ...")
    ds = rf.workspace(workspace).project(project).version(version).download(
        "yolov8", location=os.path.join("datasets", tag))
    return ds.location


def main():
    random.seed(SEED)

    # Check API key
    if ROBOFLOW_API_KEY == "YOUR_ROBOFLOW_KEY":
        has_roboflow = any("roboflow" in s for s in SOURCES)
        if has_roboflow:
            print("WARNING: ROBOFLOW_API_KEY not set. Roboflow datasets will be skipped.")
            print("         Set it with: export ROBOFLOW_API_KEY='your-key'")

    # Clean output directory
    if os.path.exists(OUT_DIR):
        print(f"Removing existing {OUT_DIR}/...")
        shutil.rmtree(OUT_DIR)

    for sp in ("train", "val"):
        os.makedirs(os.path.join(OUT_DIR, "images", sp), exist_ok=True)
        os.makedirs(os.path.join(OUT_DIR, "labels", sp), exist_ok=True)

    samples = []        # (img_path, label_path_or_None, source_tag, names_dict)
    dropped = {}        # original class name -> count dropped
    per_source = {}     # tag -> images found
    name_map_log = {}   # tag -> {orig_name -> canon_letter or 'DROPPED'}

    print("\n=== Loading sources ===")
    for src in SOURCES:
        tag = src["tag"]
        print(f"\n--- {tag} ---")

        if "roboflow" in src:
            if ROBOFLOW_API_KEY == "YOUR_ROBOFLOW_KEY":
                print(f"  [skip] No API key for Roboflow source: {tag}")
                continue
            try:
                root = download_roboflow(*src["roboflow"], tag=tag)
            except Exception as e:
                print(f"  [ERROR] Failed to download {tag}: {e}")
                continue
        else:
            root = src["local"]
            if not os.path.isdir(root):
                print(f"  [skip] Local path not found: {root}")
                print(f"         Run download_datasets.sh first to fetch external datasets.")
                continue

        yml = os.path.join(root, "data.yaml")
        if not os.path.exists(yml):
            print(f"  [skip] no data.yaml in {root}")
            continue

        names = load_names(yml)
        name_map_log[tag] = {nm: (to_letter(nm) or "DROPPED") for nm in names.values()}
        cnt = 0
        for img_dir, lab_dir in find_split_dirs(root):
            for fn in sorted(os.listdir(img_dir)):
                if not fn.lower().endswith(IMG_EXT):
                    continue
                ip = os.path.join(img_dir, fn)
                lp = os.path.join(lab_dir, os.path.splitext(fn)[0] + ".txt")
                samples.append((ip, lp if os.path.exists(lp) else None, tag, names))
                cnt += 1
        per_source[tag] = per_source.get(tag, 0) + cnt
        print(f"  {tag}: {cnt} images from {root}")

    if not samples:
        print("\nERROR: No images found from any source!")
        print("Make sure to:")
        print("  1. Set ROBOFLOW_API_KEY environment variable")
        print("  2. Run download_datasets.sh to fetch external datasets")
        sys.exit(1)

    # Dedup by image content hash
    print("\n=== Deduplicating ===")
    seen, unique = set(), []
    for ip, lp, tag, names in samples:
        try:
            h = hashlib.md5(open(ip, "rb").read()).hexdigest()
        except OSError:
            continue
        if h in seen:
            continue
        seen.add(h)
        unique.append((ip, lp, tag, names))
    dupes = len(samples) - len(unique)
    print(f"Total images: {len(samples)}  ->  unique after dedup: {len(unique)} (removed {dupes} dupes)")

    # Deterministic train/val split
    random.shuffle(unique)
    n_val = max(1, int(len(unique) * VAL_FRACTION))
    splits = {"val": unique[:n_val], "train": unique[n_val:]}

    # Copy files and remap labels
    print("\n=== Writing merged dataset ===")
    class_counts = {c: 0 for c in CANON}
    per_source_final = {tag: 0 for tag in per_source}

    for sp, items in splits.items():
        for idx, (ip, lp, tag, names) in enumerate(items):
            stem = f"{tag}_{idx}_{os.path.splitext(os.path.basename(ip))[0]}"
            ext = os.path.splitext(ip)[1].lower()
            shutil.copy(ip, os.path.join(OUT_DIR, "images", sp, stem + ext))
            per_source_final[tag] = per_source_final.get(tag, 0) + 1

            lines_out = []
            if lp:
                for line in open(lp):
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    old = int(float(parts[0]))
                    raw = names.get(old, str(old))
                    lt = to_letter(raw)
                    if lt is None:
                        dropped[raw] = dropped.get(raw, 0) + 1
                        continue
                    parts[0] = str(CIDX[lt])
                    class_counts[lt] += 1
                    lines_out.append(" ".join(parts))
            with open(os.path.join(OUT_DIR, "labels", sp, stem + ".txt"), "w") as f:
                f.write("\n".join(lines_out))

    # Write data.yaml
    with open(os.path.join(OUT_DIR, "data.yaml"), "w") as f:
        yaml.safe_dump({
            "path": os.path.abspath(OUT_DIR),
            "train": "images/train",
            "val": "images/val",
            "nc": 26,
            "names": CANON
        }, f, sort_keys=False)

    # ---- Detailed Report ----
    print("\n" + "=" * 60)
    print("  MERGE REPORT")
    print("=" * 60)

    print("\n=== Source contributions ===")
    for tag, cnt in sorted(per_source_final.items(), key=lambda x: -x[1]):
        print(f"  {tag:15s}: {cnt:5d} images")
    print(f"  {'TOTAL':15s}: {sum(per_source_final.values()):5d} images")

    print("\n=== Class-name remapping per source ===")
    for tag, mp in name_map_log.items():
        kept = {k: v for k, v in mp.items() if v != "DROPPED"}
        drp = [k for k, v in mp.items() if v == "DROPPED"]
        print(f"  {tag}: kept {len(kept)} -> {kept}")
        if drp:
            print(f"         dropped classes: {drp}")

    print("\n=== Per-class box counts (merged) ===")
    mx = max(class_counts.values()) or 1
    total_boxes = sum(class_counts.values())
    for c in CANON:
        bar = '#' * int(40 * class_counts[c] / mx)
        print(f"  {c}: {class_counts[c]:5d} {bar}")
    print(f"  TOTAL BOXES: {total_boxes}")

    # Class balance warning
    min_count = min(class_counts.values())
    max_count = max(class_counts.values())
    if min_count > 0 and max_count / min_count > 5:
        print(f"\n  ⚠️  Class imbalance detected: max/min ratio = {max_count/min_count:.1f}x")
        weak = [c for c in CANON if class_counts[c] < max_count * 0.2]
        if weak:
            print(f"     Under-represented: {', '.join(weak)}")

    if dropped:
        print("\n=== Dropped boxes (non-letter classes) ===")
        for k, v in sorted(dropped.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

    print(f"\n=== Output ===")
    print(f"  Merged dataset -> {OUT_DIR}/")
    print(f"  Train: {len(splits['train'])} images")
    print(f"  Val:   {len(splits['val'])} images")
    print(f"\n  data.yaml: {os.path.join(OUT_DIR, 'data.yaml')}")
    print(f"\n  Train command:")
    print(f"    yolo detect train data={OUT_DIR}/data.yaml model=yolov8n.pt imgsz=640 epochs=100")
    print(f"\n  Keep your OWN rig photos as a separate held-out TEST set (not merged here).")
    print("=" * 60)


if __name__ == "__main__":
    main()
