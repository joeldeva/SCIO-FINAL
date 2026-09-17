"""
app.py — BrailleVision Real-Time Braille Reader
================================================
Modes:
  python app.py                  → real-time camera (webcam index 0)
  python app.py --source img.jpg → single image
  python app.py --source video.mp4 → video file
  python app.py --source 1       → webcam index 1
"""

import argparse
import os
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

# ── Optional TTS (graceful fallback if pyttsx3 missing) ────────────────────────
try:
    import pyttsx3
    _tts_available = True
except ImportError:
    _tts_available = False
    print("[WARN] pyttsx3 not found — speech output disabled. Install with: pip install pyttsx3")

from ultralytics import YOLO

# ═══════════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_WEIGHTS   = "model/best.pt"
DEFAULT_CONF      = 0.25
DEFAULT_IOU       = 0.35
IMGSZ             = 640
ROW_GAP_RATIO     = 0.55
WORD_GAP_RATIO    = 1.2   # horizontal gap > 1.2× median char width → word boundary
SPEAK_COOLDOWN_S  = 3.0
STABILITY_FRAMES  = 8
FONT              = cv2.FONT_HERSHEY_SIMPLEX

_LETTER_TO_DIGIT = {
    'a': '1', 'b': '2', 'c': '3', 'd': '4', 'e': '5',
    'f': '6', 'g': '7', 'h': '8', 'i': '9', 'j': '0',
}


# ═══════════════════════════════════════════════════════════════════════════════
# TTS helper
# ═══════════════════════════════════════════════════════════════════════════════
class TTSEngine:
    def __init__(self, rate: int = 160):
        self._engine = None
        self._last_spoken_at = 0.0
        if _tts_available:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", rate)
            except Exception as exc:
                print(f"[WARN] TTS init failed: {exc}")
                self._engine = None

    def speak(self, text: str, force: bool = False) -> bool:
        if not self._engine or not text.strip():
            return False
        now = time.time()
        if not force and (now - self._last_spoken_at) < SPEAK_COOLDOWN_S:
            return False
        self._last_spoken_at = now
        try:
            self._engine.say(f"Braille text: {text}")
            self._engine.runAndWait()
            return True
        except Exception as exc:
            print(f"[WARN] TTS speak failed: {exc}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# Reading-order sort
# ═══════════════════════════════════════════════════════════════════════════════
def sort_detections_reading_order(boxes, names: dict) -> list[list[dict]]:
    """
    Sort detections in natural reading order (top→bottom, left→right).

    Returns list[list[dict]] — a list of rows, where each row is
    a list of detection dicts sorted left→right.  The caller decides how to
    join rows (e.g. with a space between them for word-per-row display).

    Gap-based row clustering:
      1. Sort all detections by cy.
      2. A gap > ROW_GAP_RATIO × median_height signals a new row.
    """
    if not boxes:
        return []

    dets = []
    heights = []
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        h  = y2 - y1
        heights.append(h)
        dets.append({
            "cx": cx, "cy": cy,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "label": names[int(box.cls)],
            "conf": float(box.conf),
        })

    if len(dets) == 1:
        return [dets]   # single-element row

    row_split_gap = max(15.0, float(np.median(heights)) * ROW_GAP_RATIO)

    # Sort by center-y then cluster into rows
    dets.sort(key=lambda d: d["cy"])

    rows: list[list[dict]] = []
    current_row: list[dict] = [dets[0]]

    for prev, curr in zip(dets, dets[1:]):
        gap = curr["cy"] - prev["cy"]
        if gap > row_split_gap:
            rows.append(sorted(current_row, key=lambda d: d["cx"]))
            current_row = [curr]
        else:
            current_row.append(curr)
    rows.append(sorted(current_row, key=lambda d: d["cx"]))

    return rows   # ← return rows, NOT flattened list


# ═══════════════════════════════════════════════════════════════════════════════
# Intra-row word segmentation
# ═══════════════════════════════════════════════════════════════════════════════
def split_row_into_words(row: list[dict]) -> list[list[dict]]:
    """
    Split a single left→right-sorted row into individual words by detecting
    large horizontal gaps between consecutive Braille cells.

    A gap between the right edge of one cell and the left edge of the next
    that exceeds WORD_GAP_RATIO × median_char_width is treated as a word
    boundary (space).

    Returns a list of word-groups, each being a list of detection dicts.
    """
    if not row:
        return []
    if len(row) == 1:
        return [row]

    # Median character width across all cells in this row
    widths = [d["x2"] - d["x1"] for d in row]
    median_width = float(np.median(widths))
    word_gap_threshold = max(median_width * WORD_GAP_RATIO, 10.0)

    words: list[list[dict]] = []
    current_word: list[dict] = [row[0]]

    for prev, curr in zip(row, row[1:]):
        # Gap between right edge of previous cell and left edge of current cell
        gap = curr["x1"] - prev["x2"]
        if gap > word_gap_threshold:
            words.append(current_word)
            current_word = [curr]
        else:
            current_word.append(curr)
    words.append(current_word)

    return words


# ═══════════════════════════════════════════════════════════════════════════════
# Post-processing: raw label sequence → readable text
# ═══════════════════════════════════════════════════════════════════════════════
def labels_to_text(labels: list[str]) -> str:
    """Convert a single row's label sequence to human-readable text."""
    result = []
    capitalise_next = False
    number_mode = False

    for lbl in labels:
        lbl_lower = lbl.lower().strip()

        if lbl_lower in ("space", " ", ""):
            result.append(" ")
            number_mode = False
            continue

        if lbl_lower in ("capital", "caps", "capital_indicator"):
            capitalise_next = True
            continue

        if lbl_lower in ("number", "num", "number_indicator", "#"):
            number_mode = True
            continue

        char = lbl_lower
        if number_mode:
            char = _LETTER_TO_DIGIT.get(char, char)
        elif capitalise_next:
            char = char.upper()
            capitalise_next = False

        result.append(char)

    return "".join(result)


# ═══════════════════════════════════════════════════════════════════════════════
# Core detector wrapper
# ═══════════════════════════════════════════════════════════════════════════════
class BrailleDetector:
    """Wraps YOLO inference + reading-order sort + text assembly."""

    def __init__(self, weights: str = DEFAULT_WEIGHTS,
                 conf: float = DEFAULT_CONF, iou: float = DEFAULT_IOU,
                 debug: bool = False):
        if not Path(weights).exists():
            sys.exit(f"[ERROR] Model weights not found: {weights}")
        print(f"[INFO] Loading model: {weights}")
        self.model = YOLO(weights)
        self.conf  = conf
        self.iou   = iou
        self.debug = debug
        print(f"[INFO] Model loaded  — conf={conf}  iou={iou}  debug={debug}")

    def predict_frame(self, frame: np.ndarray) -> tuple:
        """
        Run inference on a single BGR frame.

        Returns:
            results   — raw ultralytics Results object
            text      — assembled string; words within a row are separated by a
                        space (detected via horizontal gap), and rows themselves
                        are also separated by a space.
                        e.g. "cat dog mouse braille"
            dets      — flat list of detection dicts in reading order
        """
        results = self.model(
            frame,
            conf=self.conf,
            iou=self.iou,
            imgsz=IMGSZ,
            verbose=False,
        )

        all_rows: list[list[dict]] = []

        for r in results:
            if len(r.boxes) == 0:
                continue
            rows = sort_detections_reading_order(list(r.boxes), r.names)
            all_rows.extend(rows)

        # Flat detection list (for drawing / per-letter JSON)
        dets = [det for row in all_rows for det in row]

        # Build text row-by-row; within each row split into words by
        # horizontal gap, then join words with a space.
        # Final rows are also joined with a space.
        all_row_texts: list[str] = []
        for i, row in enumerate(all_rows):
            word_groups = split_row_into_words(row)
            word_texts  = [labels_to_text([d["label"] for d in wg]) for wg in word_groups]
            row_text    = " ".join(t for t in word_texts if t)

            if self.debug:
                print(f"[DEBUG] Row {i+1} — {len(word_groups)} word(s):")
                for j, wg in enumerate(word_groups):
                    print(f"          word {j+1}: {' '.join(d['label'] for d in wg)}"
                          f"  → '{word_texts[j]}'")
                print(f"          row text: {row_text!r}")

            if row_text:
                all_row_texts.append(row_text)

        text = " ".join(all_row_texts)

        if self.debug and text:
            print(f"[DEBUG] Final text : {text!r}")

        return results, text, dets


# ═══════════════════════════════════════════════════════════════════════════════
# OSD helpers
# ═══════════════════════════════════════════════════════════════════════════════
def draw_overlay(frame: np.ndarray, text: str, fps: float,
                 speaking: bool = False) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
    display_text = text if text else "— no Braille detected —"
    cv2.putText(frame, f"Braille: {display_text}", (12, 40),
                FONT, 0.9, (50, 255, 120), 2, cv2.LINE_AA)
    fps_str = f"{fps:.1f} FPS"
    (tw, _), _ = cv2.getTextSize(fps_str, FONT, 0.6, 1)
    cv2.putText(frame, fps_str, (w - tw - 10, 22),
                FONT, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
    if speaking:
        cv2.putText(frame, "◉ SPEAKING", (12, h - 40),
                    FONT, 0.6, (0, 200, 255), 2, cv2.LINE_AA)
    hint = "  s = speak   r = reset   q = quit"
    cv2.putText(frame, hint, (12, h - 12),
                FONT, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    return frame


# ═══════════════════════════════════════════════════════════════════════════════
# Image mode
# ═══════════════════════════════════════════════════════════════════════════════
def run_on_image(source: str, detector: BrailleDetector,
                 tts: TTSEngine, output_dir: str = "sample_outputs") -> str:
    frame = cv2.imread(source)
    if frame is None:
        sys.exit(f"[ERROR] Cannot read image: {source}")

    results, text, _ = detector.predict_frame(frame)
    annotated = results[0].plot()

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stem     = Path(source).stem
    out_path = str(Path(output_dir) / f"{stem}_braille_result.jpg")
    cv2.imwrite(out_path, annotated)

    print(f"\n{'─'*50}")
    print(f"  Source  : {source}")
    print(f"  Result  : {out_path}")
    print(f"  Braille : {text if text else '(none detected)'}")
    print(f"{'─'*50}\n")

    tts.speak(text, force=True)
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# Video / camera mode
# ═══════════════════════════════════════════════════════════════════════════════
def run_video(source, detector: BrailleDetector, tts: TTSEngine):
    cam_index = source
    if isinstance(source, str) and source.isdigit():
        cam_index = int(source)

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        sys.exit(f"[ERROR] Cannot open video source: {source}")

    if isinstance(cam_index, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n[INFO] BrailleVision running!")
    print("       Controls:  s = speak now   r = reset history   q = quit\n")

    fps_ema        = 30.0
    prev_time      = time.time()
    stability_buf  = deque(maxlen=STABILITY_FRAMES)
    last_auto_text = ""
    speaking       = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] End of stream or camera lost.")
            break

        results, text, _ = detector.predict_frame(frame)
        annotated = results[0].plot()

        now = time.time()
        dt  = max(now - prev_time, 1e-6)
        fps_ema   = 0.9 * fps_ema + 0.1 * (1.0 / dt)
        prev_time = now

        stability_buf.append(text)
        stable_text = text if (
            len(stability_buf) == STABILITY_FRAMES
            and len(set(stability_buf)) == 1
            and text
            and text != last_auto_text
        ) else ""

        speaking = False
        if stable_text:
            spoke = tts.speak(stable_text)
            if spoke:
                last_auto_text = stable_text
                speaking = True

        annotated = draw_overlay(annotated, text, fps_ema, speaking)
        cv2.imshow("BrailleVision", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            tts.speak(text, force=True)
        elif key == ord('r'):
            stability_buf.clear()
            last_auto_text = ""
            print("[INFO] History reset.")

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] BrailleVision stopped.")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════
def parse_args():
    parser = argparse.ArgumentParser(
        description="BrailleVision — real-time Braille to text/speech"
    )
    parser.add_argument("--source", default=None,
        help="Image/video path or webcam index (default: 0 = first webcam)")
    parser.add_argument("--weights", default=DEFAULT_WEIGHTS,
        help=f"Model weights path (default: {DEFAULT_WEIGHTS})")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF,
        help=f"Detection confidence threshold (default: {DEFAULT_CONF})")
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU,
        help=f"NMS IoU threshold (default: {DEFAULT_IOU})")
    parser.add_argument("--no-speech", action="store_true",
        help="Disable text-to-speech output")
    parser.add_argument("--debug", action="store_true",
        help="Print raw detected labels + row/word grouping to terminal each frame")
    return parser.parse_args()


def main():
    args = parse_args()
    detector = BrailleDetector(args.weights, args.conf, args.iou, debug=args.debug)
    tts = TTSEngine() if not args.no_speech else TTSEngine.__new__(TTSEngine)
    if args.no_speech:
        tts._engine = None

    source = args.source
    if source is None:
        run_video(0, detector, tts)
    else:
        img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        if Path(source).suffix.lower() in img_exts and Path(source).exists():
            run_on_image(source, detector, tts)
        else:
            run_video(source, detector, tts)


if __name__ == "__main__":
    main()