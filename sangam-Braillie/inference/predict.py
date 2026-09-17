"""
inference/predict.py — BrailleVision Batch Inference & Evaluation Tool
=======================================================================
Usage examples:

  # Single image
  python inference/predict.py --source sample_inputs/braille1.jpg

  # Entire folder of images
  python inference/predict.py --source sample_inputs/

  # Video file
  python inference/predict.py --source tests/braille_video.mp4

  # Custom weights / thresholds
  python inference/predict.py --source sample_inputs/ --weights model/best.pt --conf 0.45

  # Export predictions to JSON
  python inference/predict.py --source sample_inputs/ --export-json

  # Use ONNX model (faster CPU inference)
  python inference/predict.py --source sample_inputs/ --weights model/best.onnx

  # Disable robust dual-pass (faster but may miss low-contrast letters)
  python inference/predict.py --source sample_inputs/ --no-enhance

  # Disable tiled (sliced) inference — quicker but misses small letters in big images
  python inference/predict.py --source sample_inputs/ --no-tile
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# ── Sibling import: reuse shared logic from app.py ─────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app import (
    BrailleDetector,
    labels_to_text,
    sort_detections_reading_order,
    DEFAULT_CONF,
    DEFAULT_IOU,
    IMGSZ,
)

# ── Supported extensions ────────────────────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

DEFAULT_WEIGHTS    = "model/best.pt"
DEFAULT_OUTPUT_DIR = "sample_outputs"

# ── Visual constants ────────────────────────────────────────────────────────────
FONT       = cv2.FONT_HERSHEY_SIMPLEX
_CONF_HIGH = (50,  220, 80)    # BGR green
_CONF_MED  = (0,   200, 255)   # BGR amber/yellow
_CONF_LOW  = (50,  80,  255)   # BGR red
_GAP_COLOR = (200, 200, 200)   # BGR light-grey — placeholder gap boxes


# ═══════════════════════════════════════════════════════════════════════════════
# Preprocessing
# ═══════════════════════════════════════════════════════════════════════════════
def enhance_frame(frame: np.ndarray,
                  clahe_clip: float = 2.5,
                  unsharp_amount: float = 1.4,
                  gamma: float = 0.85) -> np.ndarray:
    """
    Lighter-touch enhancement than the previous version: CLAHE → mild unsharp
    → gentle gamma. Heavy unsharp + 0.75 gamma was inventing dots from shadow
    noise, which is exactly what produced the wrong-class duplicates ("A/L/L"
    stacked at the same location) in the failing example.

    All knobs are parameterised so callers can dial them per-image.
    """
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe   = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
    gray    = clahe.apply(gray)
    blurred = cv2.GaussianBlur(gray, (3, 3), sigmaX=0)
    heavy   = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.0)
    sharp   = cv2.addWeighted(blurred, 1.0 + unsharp_amount,
                              heavy,  -unsharp_amount, 0)
    if abs(gamma - 1.0) > 1e-3:
        lut = np.array(
            [min(255, int(((i / 255.0) ** gamma) * 255)) for i in range(256)],
            dtype=np.uint8,
        )
        sharp = cv2.LUT(sharp, lut)
    return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)


# ═══════════════════════════════════════════════════════════════════════════════
# NMS helpers
# ═══════════════════════════════════════════════════════════════════════════════
def _iou(a: list[float], b: list[float]) -> float:
    ix1 = max(a[0], b[0]);  iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]);  iy2 = min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def _center_distance_norm(a: dict, b: dict) -> float:
    """Center-distance normalised by the average box width — robust 'same cell?' test."""
    avg_w = ((a["x2"] - a["x1"]) + (b["x2"] - b["x1"])) * 0.5
    if avg_w <= 0:
        return float("inf")
    return float(np.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"]) / avg_w)


def nms_merge(boxes: list[dict],
              iou_thresh: float = 0.45,
              center_thresh: float = 0.35) -> list[dict]:
    """
    Class-aware merge with two suppression criteria:
      1. IoU > iou_thresh                → same physical box, same/different class
      2. Center-distance / box-width < center_thresh
                                          → same Braille cell detected as
                                            different classes by different passes
                                            (this is the failure mode that
                                            produced the stacked 'A/L/L' labels
                                            in the failing example).

    Keeps the highest-confidence detection in each cluster.
    """
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b["conf"], reverse=True)
    kept: list[dict] = []
    for cand in boxes:
        duplicate = False
        for k in kept:
            if _iou(cand["xyxy"], k["xyxy"]) >= iou_thresh:
                duplicate = True
                break
            if _center_distance_norm(cand, k) < center_thresh:
                duplicate = True
                break
        if not duplicate:
            kept.append(cand)
    return kept


# ═══════════════════════════════════════════════════════════════════════════════
# Auto-ROI: focus on the dense detection cluster so the model isn't wasting
# resolution on the empty cardboard around the Braille text.
# ═══════════════════════════════════════════════════════════════════════════════
def compute_roi(dets: list[dict], frame_shape: tuple[int, int],
                pad_frac: float = 0.08) -> tuple[int, int, int, int] | None:
    """
    Build a tight rectangle around all current detections, then pad by
    `pad_frac` of its own size. Returns (x1, y1, x2, y2) in frame coords,
    or None if there aren't enough detections to trust.
    """
    if len(dets) < 3:
        return None
    h, w = frame_shape[:2]
    x1 = min(d["x1"] for d in dets)
    y1 = min(d["y1"] for d in dets)
    x2 = max(d["x2"] for d in dets)
    y2 = max(d["y2"] for d in dets)
    bw, bh = x2 - x1, y2 - y1
    pad_x, pad_y = bw * pad_frac, bh * pad_frac
    x1 = max(0,     int(x1 - pad_x))
    y1 = max(0,     int(y1 - pad_y))
    x2 = min(w - 1, int(x2 + pad_x))
    y2 = min(h - 1, int(y2 + pad_y))
    if x2 - x1 < 40 or y2 - y1 < 40:
        return None
    return (x1, y1, x2, y2)


# ═══════════════════════════════════════════════════════════════════════════════
# Tiled / sliced inference (the big-win for high-res docs)
# ═══════════════════════════════════════════════════════════════════════════════
def _run_single_pass(model: YOLO, frame: np.ndarray,
                     conf: float, iou: float, imgsz: int,
                     augment: bool = False) -> list[dict]:
    """Run one YOLO pass and return raw box dicts."""
    results = model(frame, conf=conf, iou=iou, imgsz=imgsz,
                    augment=augment, verbose=False)
    boxes: list[dict] = []
    for r in results:
        if len(r.boxes) == 0:
            continue
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            boxes.append({
                "xyxy":  [x1, y1, x2, y2],
                "cx":    (x1 + x2) / 2,
                "cy":    (y1 + y2) / 2,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "label": r.names[int(box.cls)],
                "conf":  float(box.conf),
                "cls":   int(box.cls),
            })
    return boxes


def _tiled_pass(model: YOLO, frame: np.ndarray,
                conf: float, iou: float, imgsz: int,
                tile_size: int, overlap: float) -> list[dict]:
    """
    Slice the frame into overlapping tiles, run inference on each, and
    translate the boxes back to global coordinates. This is the standard
    SAHI-style trick that dramatically improves recall on small objects
    in large images.

    `tile_size` is the tile side in original-image pixels.
    `overlap`   is the fractional overlap between adjacent tiles (0–0.5).
    """
    h, w = frame.shape[:2]
    if h <= tile_size and w <= tile_size:
        # Image already smaller than one tile — fall back to normal pass
        return _run_single_pass(model, frame, conf, iou, imgsz)

    stride = max(1, int(tile_size * (1.0 - overlap)))
    xs = list(range(0, max(1, w - tile_size + 1), stride))
    ys = list(range(0, max(1, h - tile_size + 1), stride))
    # Ensure we cover the right/bottom edges
    if xs[-1] + tile_size < w:
        xs.append(max(0, w - tile_size))
    if ys[-1] + tile_size < h:
        ys.append(max(0, h - tile_size))

    out: list[dict] = []
    for ty in ys:
        for tx in xs:
            tile = frame[ty:ty + tile_size, tx:tx + tile_size]
            if tile.size == 0:
                continue
            boxes = _run_single_pass(model, tile, conf, iou, imgsz)
            # Translate back to global coords
            for b in boxes:
                b["x1"] += tx;  b["x2"] += tx
                b["y1"] += ty;  b["y2"] += ty
                b["cx"] += tx;  b["cy"] += ty
                b["xyxy"] = [b["x1"], b["y1"], b["x2"], b["y2"]]
            out.extend(boxes)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Robust inference — adaptive cascade
# ═══════════════════════════════════════════════════════════════════════════════
def run_robust_inference(
    detector: BrailleDetector,
    frame: np.ndarray,
    use_enhance: bool = True,
    use_tile: bool = True,
    scales: list[int] | None = None,
    scout_conf_factor: float = 0.5,
    tile_overlap: float = 0.25,
) -> tuple[list[dict], np.ndarray]:
    """
    Adaptive multi-pass inference strategy.

    Pass 1 — full image at the model's native scale.
    Pass 2 — full image at a larger scale (adaptive: at least 1.5× frame
             longest side, capped at the largest requested scale) with TTA
             (`augment=True`) to flush out borderline detections.
    Pass 3 — only if pass 1+2 found very few detections OR the detection
             cluster covers a small fraction of the frame: re-run on an
             auto-cropped ROI so faint dots are sampled at higher relative
             resolution. (This directly addresses the failure mode in your
             first image where the Braille only fills ~30% of the frame.)
    Pass 4 — sliced/tiled inference for high-resolution images. Tile size
             is adaptive to image dimensions. Lower conf threshold because
             we'll dedupe via NMS afterwards.
    Pass 5 — gentle CLAHE-enhanced pass at native scale, low conf.

    All passes are merged with class-aware NMS that suppresses both
    IoU-overlapping boxes AND center-coincident boxes of different classes
    (which is what produced the messy 'A/L/L' stacks in the failing run).
    """
    h, w = frame.shape[:2]
    long_side = max(h, w)

    if scales is None:
        # Adaptive default: native + ~2× longest side, snapped to multiples of 32
        s1 = 640
        s2 = max(960, min(1920, int(np.ceil(long_side * 1.25 / 32.0) * 32)))
        scales = sorted({s1, s2})

    base_conf  = detector.conf
    scout_conf = max(0.05, base_conf * scout_conf_factor)

    all_raw: list[dict] = []

    # ── Pass 1: full image at primary scale, normal conf ───────────────────────
    all_raw.extend(
        _run_single_pass(detector.model, frame,
                         base_conf, detector.iou, scales[0])
    )

    # ── Pass 2: larger scale + TTA, scout conf ────────────────────────────────
    if len(scales) > 1:
        all_raw.extend(
            _run_single_pass(detector.model, frame,
                             scout_conf, detector.iou, scales[-1],
                             augment=True)
        )

    # First dedupe so the ROI computation below isn't biased by duplicates
    interim = nms_merge(all_raw, iou_thresh=0.45, center_thresh=0.35)

    # ── Pass 3: ROI re-inference if Braille region is small relative to frame ─
    roi = compute_roi(interim, frame.shape, pad_frac=0.10) if interim else None
    if roi is not None:
        rx1, ry1, rx2, ry2 = roi
        roi_area  = (rx2 - rx1) * (ry2 - ry1)
        frm_area  = h * w
        # Trigger if Braille fills less than ~55% of the frame, OR fewer than
        # 12 detections so far (likely missing letters)
        if roi_area / frm_area < 0.55 or len(interim) < 12:
            roi_crop = frame[ry1:ry2, rx1:rx2]
            roi_boxes = _run_single_pass(
                detector.model, roi_crop,
                scout_conf, detector.iou, scales[-1],
                augment=True,
            )
            for b in roi_boxes:
                b["x1"] += rx1;  b["x2"] += rx1
                b["y1"] += ry1;  b["y2"] += ry1
                b["cx"] += rx1;  b["cy"] += ry1
                b["xyxy"] = [b["x1"], b["y1"], b["x2"], b["y2"]]
            all_raw.extend(roi_boxes)

    # ── Pass 4: tiled inference for high-resolution images ────────────────────
    if use_tile and long_side >= 1280:
        # Tile sized so each tile is roughly the model's native input
        tile_size = min(long_side, max(640, int(long_side / 2)))
        all_raw.extend(
            _tiled_pass(detector.model, frame,
                        scout_conf, detector.iou,
                        imgsz=scales[0],
                        tile_size=tile_size,
                        overlap=tile_overlap)
        )

    # ── Pass 5: gentle CLAHE-enhanced pass ────────────────────────────────────
    if use_enhance:
        enhanced = enhance_frame(frame)
        all_raw.extend(
            _run_single_pass(detector.model, enhanced,
                             scout_conf, detector.iou, scales[0])
        )

    # ── Final class-aware merge ───────────────────────────────────────────────
    dets = nms_merge(all_raw, iou_thresh=0.45, center_thresh=0.35)

    # Reading-order rows for downstream consumers / annotation
    rows = _sort_dets_into_rows(dets) if dets else []
    flat_dets = [d for row in rows for d in row]
    annotated = draw_rich_annotation(frame, flat_dets, rows=rows)

    return flat_dets, annotated


def _sort_dets_into_rows(dets: list[dict]) -> list[list[dict]]:
    """Gap-based row clustering (same algorithm as in app.py, on dict format)."""
    if not dets:
        return []
    if len(dets) == 1:
        return [dets]

    ROW_GAP_RATIO = 0.55
    heights = [d["y2"] - d["y1"] for d in dets]
    row_split_gap = max(15.0, float(np.median(heights)) * ROW_GAP_RATIO)

    sorted_by_cy = sorted(dets, key=lambda d: d["cy"])
    rows: list[list[dict]] = []
    current: list[dict] = [sorted_by_cy[0]]

    for prev, curr in zip(sorted_by_cy, sorted_by_cy[1:]):
        if curr["cy"] - prev["cy"] > row_split_gap:
            rows.append(sorted(current, key=lambda d: d["cx"]))
            current = [curr]
        else:
            current.append(curr)
    rows.append(sorted(current, key=lambda d: d["cx"]))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# Spatial gap detector
# ═══════════════════════════════════════════════════════════════════════════════
def detect_row_gaps(rows: list[list[dict]],
                    gap_multiplier: float = 1.8) -> list[dict]:
    """
    Find positions where a Braille cell was probably present but not detected.

    For each row: compute the median cell-step (width + inter-cell gap). Any
    actual gap > `gap_multiplier` × step is treated as one or more missed cells.
    """
    gap_dets: list[dict] = []

    for row in rows:
        if len(row) < 2:
            continue

        widths = [d["x2"] - d["x1"] for d in row]
        med_w  = float(np.median(widths))

        inter_gaps = [row[i+1]["x1"] - row[i]["x2"] for i in range(len(row)-1)]
        med_gap    = float(np.median(inter_gaps)) if inter_gaps else med_w * 0.3

        step = med_w + med_gap
        if step <= 0:
            continue

        threshold = gap_multiplier * step

        for i in range(len(row) - 1):
            actual_gap = row[i+1]["x1"] - row[i]["x2"]
            if actual_gap > threshold:
                n_missed = max(1, round(actual_gap / step) - 1)
                for k in range(1, n_missed + 1):
                    cx_est = row[i]["x2"] + k * step - med_w / 2
                    avg_y1 = (row[i]["y1"] + row[i+1]["y1"]) / 2
                    avg_y2 = (row[i]["y2"] + row[i+1]["y2"]) / 2
                    gap_dets.append({
                        "xyxy":  [cx_est - med_w/2, avg_y1,
                                  cx_est + med_w/2, avg_y2],
                        "x1": cx_est - med_w/2, "y1": avg_y1,
                        "x2": cx_est + med_w/2, "y2": avg_y2,
                        "cx": cx_est, "cy": (avg_y1 + avg_y2) / 2,
                        "label": "?",
                        "conf":  0.0,
                        "is_gap": True,
                    })

    return gap_dets


# ═══════════════════════════════════════════════════════════════════════════════
# Rich visual annotation
# ═══════════════════════════════════════════════════════════════════════════════
def _conf_color(conf: float) -> tuple[int, int, int]:
    if conf >= 0.75:
        return _CONF_HIGH
    elif conf >= 0.50:
        return _CONF_MED
    return _CONF_LOW


def draw_rich_annotation(
    frame: np.ndarray,
    dets: list[dict],
    rows: list[list[dict]] | None = None,
    show_gaps: bool = True,
) -> np.ndarray:
    """
    Annotated frame with:
      • Bounding box, label, confidence, colour-coded by conf
      • Dashed grey boxes at detected gap positions
      • Row text strip on the left
      • Bottom summary banner
    """
    out = frame.copy()
    h, w = out.shape[:2]

    gap_dets: list[dict] = []
    if show_gaps and rows:
        gap_dets = detect_row_gaps(rows)

    # Dashed gap boxes
    for gd in gap_dets:
        x1, y1, x2, y2 = int(gd["x1"]), int(gd["y1"]), int(gd["x2"]), int(gd["y2"])
        bw, bh = x2 - x1, y2 - y1
        dash, gap_px = 8, 5
        for side in range(4):
            length = bw if side % 2 == 0 else bh
            for s in range(0, length, dash + gap_px):
                e = min(s + dash, length)
                if side == 0:
                    cv2.line(out, (x1+s, y1), (x1+e, y1), _GAP_COLOR, 2)
                elif side == 1:
                    cv2.line(out, (x2, y1+s), (x2, y1+e), _GAP_COLOR, 2)
                elif side == 2:
                    cv2.line(out, (x2-s, y2), (x2-e, y2), _GAP_COLOR, 2)
                elif side == 3:
                    cv2.line(out, (x1, y2-s), (x1, y2-e), _GAP_COLOR, 2)
        cv2.putText(out, "?", (x1 + 4, y2 - 6),
                    FONT, 0.55, _GAP_COLOR, 2, cv2.LINE_AA)

    # Real detections — scale font/thickness with box size so labels stay readable
    # on any image size (no hardcoded font scale).
    for det in dets:
        x1, y1, x2, y2 = int(det["x1"]), int(det["y1"]), int(det["x2"]), int(det["y2"])
        box_h = max(1, y2 - y1)
        font_scale = float(np.clip(box_h / 60.0, 0.40, 0.95))
        font_thick = 1 if font_scale < 0.6 else 2

        color = _conf_color(det["conf"])
        label_str = f"{det['label'].upper()} {det['conf']:.2f}"
        (tw, th), bl = cv2.getTextSize(label_str, FONT, font_scale, font_thick)
        label_y = max(y1 - 4, th + 4)
        cv2.rectangle(out, (x1, label_y - th - 4),
                      (x1 + tw + 4, label_y + bl), color, -1)
        cv2.putText(out, label_str, (x1 + 2, label_y),
                    FONT, font_scale, (0, 0, 0), font_thick, cv2.LINE_AA)

        thickness = 3 if det["conf"] >= 0.75 else 2
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)

    # Row strip on left
    if rows:
        row_y_centres = [(min(d["cy"] for d in row), row) for row in rows]
        for cy, row in row_y_centres:
            all_in_row = sorted(
                [d for d in row] +
                [g for g in gap_dets if abs(g["cy"] - cy) < 20],
                key=lambda d: d["cx"]
            )
            row_str = "".join(
                "?" if d.get("is_gap") else d["label"].upper()
                for d in all_in_row
            )
            cv2.putText(out, row_str, (6, int(cy) + 5),
                        FONT, 0.6, (230, 230, 230), 2, cv2.LINE_AA)

    # Bottom banner
    n_det  = len(dets)
    n_gap  = len(gap_dets)
    banner = f"  {n_det} detected"
    if n_gap:
        banner += f"  |  {n_gap} gap(s) flagged"
    if n_det:
        avg_conf = sum(d["conf"] for d in dets) / n_det
        banner += f"  |  avg conf {avg_conf:.2f}"

    strip = out.copy()
    cv2.rectangle(strip, (0, h - 36), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(strip, 0.55, out, 0.45, 0, out)
    cv2.putText(out, banner, (6, h - 10),
                FONT, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Collect input files
# ═══════════════════════════════════════════════════════════════════════════════
def collect_inputs(source: str) -> tuple[list[Path], list[Path]]:
    src = Path(source)
    images, videos = [], []
    if src.is_file():
        ext = src.suffix.lower()
        if ext in IMAGE_EXTS:
            images.append(src)
        elif ext in VIDEO_EXTS:
            videos.append(src)
        else:
            sys.exit(f"[ERROR] Unsupported file extension: {ext}")
    elif src.is_dir():
        for f in sorted(src.iterdir()):
            ext = f.suffix.lower()
            if ext in IMAGE_EXTS:
                images.append(f)
            elif ext in VIDEO_EXTS:
                videos.append(f)
        if not images and not videos:
            sys.exit(f"[ERROR] No supported files found in directory: {src}")
    else:
        sys.exit(f"[ERROR] Source not found: {source}")
    return images, videos


# ═══════════════════════════════════════════════════════════════════════════════
# Per-image inference
# ═══════════════════════════════════════════════════════════════════════════════
def predict_image(
    image_path: Path,
    detector: BrailleDetector,
    output_dir: Path,
    save_annotated: bool = True,
    use_enhance: bool = True,
    use_tile: bool = True,
    scales: list[int] | None = None,
) -> dict:
    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"  [SKIP] Cannot read: {image_path}")
        return {}

    t0 = time.perf_counter()
    dets, annotated = run_robust_inference(
        detector, frame,
        use_enhance=use_enhance,
        use_tile=use_tile,
        scales=scales,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    rows = _sort_dets_into_rows(dets)
    row_texts = [labels_to_text([d["label"] for d in row]) for row in rows]
    text = " ".join(t for t in row_texts if t)

    gap_dets = detect_row_gaps(rows) if rows else []

    saved_to = None
    if save_annotated:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{image_path.stem}_result{image_path.suffix}"
        cv2.imwrite(str(out_path), annotated)
        saved_to = str(out_path)

    return {
        "path":           str(image_path),
        "text":           text,
        "num_detections": len(dets),
        "num_gaps":       len(gap_dets),
        "labels":         [d["label"] for d in dets],
        "confidences":    [round(d["conf"], 4) for d in dets],
        "inference_ms":   round(elapsed_ms, 2),
        "saved_to":       saved_to,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Per-video inference
# ═══════════════════════════════════════════════════════════════════════════════
def predict_video(
    video_path: Path,
    detector: BrailleDetector,
    output_dir: Path,
    sample_every_n: int = 5,
    use_enhance: bool = True,
    use_tile: bool = True,
    scales: list[int] | None = None,
) -> dict:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  [SKIP] Cannot open video: {video_path}")
        return {}

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = output_dir / f"{video_path.stem}_result.mp4"
    writer   = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps, (width, height)
    )

    frame_idx      = 0
    all_row_texts: list[str] = []
    total_ms       = 0.0
    processed      = 0
    last_annotated = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every_n == 0:
            t0 = time.perf_counter()
            # For video, tiling is usually too slow per-frame — keep it optional.
            dets, last_annotated = run_robust_inference(
                detector, frame,
                use_enhance=use_enhance,
                use_tile=use_tile,
                scales=scales,
            )
            total_ms += (time.perf_counter() - t0) * 1000
            rows = _sort_dets_into_rows(dets)
            row_texts = [labels_to_text([d["label"] for d in row]) for row in rows]
            frame_text = " ".join(t for t in row_texts if t)
            if frame_text:
                all_row_texts.append(frame_text)
            processed += 1

        writer.write(last_annotated if last_annotated is not None else frame)
        frame_idx += 1

    cap.release()
    writer.release()

    text = _most_common(all_row_texts) if all_row_texts else ""

    return {
        "path":             str(video_path),
        "text":             text,
        "total_frames":     frame_idx,
        "frames_inferred":  processed,
        "avg_inference_ms": round(total_ms / max(processed, 1), 2),
        "saved_to":         str(out_path),
    }


def _most_common(lst: list[str]) -> str:
    from collections import Counter
    if not lst:
        return ""
    return Counter(lst).most_common(1)[0][0]


# ═══════════════════════════════════════════════════════════════════════════════
# Pretty-print results
# ═══════════════════════════════════════════════════════════════════════════════
def print_results(results: list[dict]):
    total    = len(results)
    detected = sum(1 for r in results if r.get("text"))
    total_ms = sum(r.get("inference_ms", 0) for r in results)
    total_gaps = sum(r.get("num_gaps", 0) for r in results)

    print("\n" + "═" * 62)
    print("  BrailleVision — Batch Inference Summary")
    print("═" * 62)

    for i, r in enumerate(results, 1):
        name  = Path(r["path"]).name
        text  = r.get("text") or "(none detected)"
        n_det = r.get("num_detections", "—")
        n_gap = r.get("num_gaps", 0)
        ms    = r.get("inference_ms", "—")
        print(f"\n  [{i:02d}] {name}")
        print(f"       Text       : {text}")
        print(f"       Detections : {n_det}"
              + (f"  ({n_gap} gap(s) flagged)" if n_gap else ""))
        print(f"       Time       : {ms} ms")
        if r.get("saved_to"):
            print(f"       Saved to   : {r['saved_to']}")

    print("\n" + "─" * 62)
    print(f"  Files processed  : {total}")
    print(f"  With detections  : {detected} / {total}")
    if total_gaps:
        print(f"  Total gaps flagged: {total_gaps}  (shown as '?' in output images)")
    if total > 0:
        print(f"  Avg. infer. time : {total_ms / total:.1f} ms/frame")
    print("═" * 62 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════
def parse_args():
    parser = argparse.ArgumentParser(
        description="BrailleVision batch inference / evaluation tool"
    )
    parser.add_argument("--source", required=True,
                        help="Image, video, or folder path")
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS,
                        help=f"Model weights (default: {DEFAULT_WEIGHTS})")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF,
                        help=f"Confidence threshold (default: {DEFAULT_CONF})")
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU,
                        help=f"NMS IoU threshold (default: {DEFAULT_IOU})")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Directory for annotated outputs (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--no-save", action="store_true",
                        help="Skip saving annotated output images/video")
    parser.add_argument("--export-json", action="store_true",
                        help="Export results to results.json in --output-dir")
    parser.add_argument("--sample-every", type=int, default=5,
                        help="For videos: run inference every N frames (default: 5)")
    parser.add_argument("--no-enhance", action="store_true",
                        help="Disable enhanced preprocessing pass")
    parser.add_argument("--no-tile", action="store_true",
                        help="Disable tiled (sliced) inference for large images")
    parser.add_argument("--scales", nargs="+", type=int, default=None,
                        help="Image sizes for multi-scale inference "
                             "(default: adaptive from image dimensions)")
    return parser.parse_args()


def main():
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    detector = BrailleDetector(args.weights, args.conf, args.iou)
    images, videos = collect_inputs(args.source)
    use_enhance = not args.no_enhance
    use_tile    = not args.no_tile

    print(f"\n[INFO] Found {len(images)} image(s) and {len(videos)} video(s).")
    print(f"[INFO] Robust inference: enhance={use_enhance}  tile={use_tile}  "
          f"scales={'adaptive' if args.scales is None else args.scales}\n")

    all_results: list[dict] = []

    for img_path in images:
        print(f"  Processing image: {img_path.name}", end=" ", flush=True)
        r = predict_image(
            img_path, detector, output_dir,
            save_annotated=not args.no_save,
            use_enhance=use_enhance,
            use_tile=use_tile,
            scales=args.scales,
        )
        if r:
            all_results.append(r)
            gap_note = f" ({r['num_gaps']} gap(s) flagged)" if r["num_gaps"] else ""
            print(f"→ {r['text'] or '(no detection)'}{gap_note}")

    for vid_path in videos:
        print(f"  Processing video: {vid_path.name} …")
        r = predict_video(
            vid_path, detector, output_dir,
            args.sample_every,
            use_enhance=use_enhance,
            use_tile=use_tile,
            scales=args.scales,
        )
        if r:
            all_results.append(r)
            print(f"    → {r['text'] or '(no detection)'}")

    if all_results:
        print_results(all_results)

    if args.export_json:
        json_path = output_dir / "results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Results exported to: {json_path}")


if __name__ == "__main__":
    main()
