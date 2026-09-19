#!/usr/bin/env python3
"""
Final BrailleVision live scanner.

Run:
    python final_live_app.py

Open:
    http://127.0.0.1:8088

For phone testing on the same Wi-Fi:
    http://<laptop-ip>:8088

Note: browser camera access on phones usually requires HTTPS. Laptop Chrome/Edge
on localhost works over HTTP.
"""

from __future__ import annotations

import base64
import asyncio
import os
import threading
from collections import Counter, deque
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from ultralytics import YOLO

from inference import preprocess
from lms_api import router as lms_router

try:
    from spellchecker import SpellChecker
except ImportError:
    SpellChecker = None


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", BASE_DIR / "model" / "best.pt"))
CONFIDENCE = float(os.environ.get("BRAILLE_CONF", "0.50"))
IOU = float(os.environ.get("BRAILLE_IOU", "0.50"))
DUPLICATE_IOU = float(os.environ.get("BRAILLE_DUPLICATE_IOU", "0.70"))
IMGSZ = int(os.environ.get("BRAILLE_IMGSZ", "640"))
MAX_UPLOAD_BYTES = int(os.environ.get("BRAILLE_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
MAX_IMAGE_PIXELS = int(os.environ.get("BRAILLE_MAX_IMAGE_PIXELS", str(32_000_000)))
ENHANCE_IMAGE = os.environ.get("BRAILLE_ENHANCE", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AUGMENT_INFERENCE = os.environ.get("BRAILLE_AUGMENT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HISTORY_SIZE = int(os.environ.get("BRAILLE_HISTORY", "5"))
SPACE_GAP_MULTIPLIER = float(os.environ.get("BRAILLE_SPACE_GAP_MULTIPLIER", "1.8"))
SPACE_WIDTH_MULTIPLIER = float(os.environ.get("BRAILLE_SPACE_WIDTH_MULTIPLIER", "1.35"))
FLIP_HORIZONTAL = os.environ.get("BRAILLE_FLIP_HORIZONTAL", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if not MODEL_PATH.is_file():
    raise RuntimeError(f"Braille model not found: {MODEL_PATH}")

app = FastAPI(title="Sciobraille Live Scanner")
app.include_router(lms_router)
model = YOLO(str(MODEL_PATH))
names = model.names
predict_lock = threading.Lock()
client_histories: dict[str, deque[str]] = {}
history_lock = threading.Lock()
spell = SpellChecker() if SpellChecker is not None else None


FUTURE_CLASS_SCHEMA = [
    "number_indicator",
    "capital_indicator",
    "space",
    "period",
    "comma",
    "question",
    "exclamation",
    "colon",
    "semicolon",
    "apostrophe",
    "hyphen",
    "the",
    "and",
    "for",
    "of",
    "with",
]

CELL_TEXT = {
    "space": " ",
    "blank": " ",
    "period": ".",
    ".": ".",
    "comma": ",",
    ",": ",",
    "question": "?",
    "?": "?",
    "exclamation": "!",
    "!": "!",
    "colon": ":",
    ":": ":",
    "semicolon": ";",
    ";": ";",
    "apostrophe": "'",
    "'": "'",
    "hyphen": "-",
    "-": "-",
    "dash": "-",
    "the": "the",
    "and": "and",
    "for": "for",
    "of": "of",
    "with": "with",
}

NUMBER_MAP = {
    "a": "1",
    "b": "2",
    "c": "3",
    "d": "4",
    "e": "5",
    "f": "6",
    "g": "7",
    "h": "8",
    "i": "9",
    "j": "0",
}


KNOWN_WORDS = [
    "dmi",
    "college",
    "engineering",
    "jaihind",
    "india",
    "sciobraille",
    "visually",
    "impaired",
    "great",
    "project",
]

EXACT_CORRECTIONS = {
    "isually": "visually",
    "visuall": "visually",
    "visualy": "visually",
    "jaihiqd": "jaihind",
    "jaihid": "jaihind",
    "jaihnd": "jaihind",
    "hindia": "india",
    "scobraille": "sciobraille",
    "scio braille": "sciobraille",
    "impared": "impaired",
    "impaire": "impaired",
    "projct": "project",
}


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sciobraille Live Scanner</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0d1117;
      --panel: #151b23;
      --line: #2b3440;
      --text: #f1f5f9;
      --muted: #8b949e;
      --green: #36c75a;
      --green-2: #1f8f3d;
      --red: #ef4444;
      --yellow: #fbbf24;
      --blue: #38bdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.65fr);
      gap: 0;
    }
    .camera {
      position: relative;
      min-height: 100vh;
      background: #05070a;
      overflow: hidden;
      border-right: 1px solid var(--line);
    }
    video {
      width: 100%;
      height: 100%;
      min-height: 100vh;
      object-fit: cover;
      background: #05070a;
    }
    .scan-frame {
      position: absolute;
      inset: 32px;
      pointer-events: none;
      border: 1px solid rgba(54, 199, 90, 0.3);
    }
    .corner {
      position: absolute;
      width: 34px;
      height: 34px;
      border-color: var(--green);
      border-style: solid;
    }
    .tl { top: 0; left: 0; border-width: 3px 0 0 3px; }
    .tr { top: 0; right: 0; border-width: 3px 3px 0 0; }
    .bl { bottom: 0; left: 0; border-width: 0 0 3px 3px; }
    .br { bottom: 0; right: 0; border-width: 0 3px 3px 0; }
    .status {
      position: absolute;
      left: 24px;
      bottom: 24px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      background: rgba(13, 17, 23, 0.84);
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--muted);
    }
    .dot.on { background: var(--green); box-shadow: 0 0 12px rgba(54, 199, 90, 0.8); }
    .side {
      min-height: 100vh;
      background: var(--panel);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    h1 {
      margin: 0;
      font-size: clamp(24px, 3vw, 34px);
      line-height: 1.05;
      letter-spacing: 0;
    }
    .sub {
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.45;
      font-size: 14px;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    button {
      border: 1px solid var(--line);
      background: #202835;
      color: var(--text);
      border-radius: 8px;
      padding: 13px 14px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    button.primary {
      background: var(--green);
      color: #031107;
      border-color: var(--green-2);
    }
    button.danger {
      background: #2a161a;
      border-color: #5f252e;
      color: #fecdd3;
    }
    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .toggle {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
      user-select: none;
    }
    .toggle input { width: 18px; height: 18px; }
    .output {
      flex: 1;
      min-height: 260px;
      background: #0f141b;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      white-space: pre-wrap;
      font-family: "Segoe UI", system-ui, sans-serif;
      font-size: clamp(24px, 4.5vw, 44px);
      line-height: 1.25;
      letter-spacing: 0;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      background: #0f141b;
      border-radius: 8px;
      padding: 12px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .metric strong { font-size: 18px; }
    .hint {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin: 0;
    }
    canvas { display: none; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .camera { min-height: 46vh; border-right: 0; border-bottom: 1px solid var(--line); }
      video { min-height: 46vh; height: 46vh; }
      .side { min-height: 54vh; }
      .scan-frame { inset: 18px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="camera">
      <video id="video" playsinline muted></video>
      <canvas id="canvas"></canvas>
      <div class="scan-frame" aria-hidden="true">
        <div class="corner tl"></div><div class="corner tr"></div>
        <div class="corner bl"></div><div class="corner br"></div>
      </div>
      <div class="status"><span id="statusDot" class="dot"></span><span id="status">Ready</span></div>
    </section>
    <section class="side">
      <header>
        <h1>Sciobraille Live</h1>
        <p class="sub">Point the camera at physical Braille. Hold steady until the text stabilizes.</p>
      </header>
      <div class="controls">
        <button id="scanBtn" class="primary">Scan</button>
        <button id="stopBtn" class="danger" disabled>Stop</button>
      </div>
      <label class="toggle"><input id="autoSpeak" type="checkbox" /> Auto speak stable text</label>
      <button id="speakBtn">Speak Text</button>
      <div id="output" class="output">Click Scan</div>
      <div class="metrics">
        <div class="metric"><span>Detections</span><strong id="detections">0</strong></div>
        <div class="metric"><span>Confidence</span><strong id="confidence">0%</strong></div>
        <div class="metric"><span>Stable</span><strong id="stable">No</strong></div>
      </div>
      <p class="hint" id="hint">For phone camera access, browsers may require HTTPS. Laptop localhost works over HTTP.</p>
    </section>
  </main>
  <script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const scanBtn = document.getElementById('scanBtn');
    const stopBtn = document.getElementById('stopBtn');
    const output = document.getElementById('output');
    const statusEl = document.getElementById('status');
    const statusDot = document.getElementById('statusDot');
    const detectionsEl = document.getElementById('detections');
    const confidenceEl = document.getElementById('confidence');
    const stableEl = document.getElementById('stable');
    const speakBtn = document.getElementById('speakBtn');
    const autoSpeak = document.getElementById('autoSpeak');

    let stream = null;
    let timer = null;
    let busy = false;
    let lastSpoken = '';
    const intervalMs = 1800;

    function setStatus(text, active=false) {
      statusEl.textContent = text;
      statusDot.classList.toggle('on', active);
    }

    function speak(text) {
      if (!text || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.replace(/\n/g, '. '));
      utterance.rate = 0.92;
      window.speechSynthesis.speak(utterance);
    }

    async function startScan() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false
        });
      } catch (err) {
        output.textContent = 'Camera access failed';
        setStatus('Camera blocked');
        document.getElementById('hint').textContent = err.message || String(err);
        return;
      }
      video.srcObject = stream;
      await video.play();
      scanBtn.disabled = true;
      stopBtn.disabled = false;
      setStatus('Scanning', true);
      captureAndSend();
      timer = setInterval(captureAndSend, intervalMs);
    }

    function stopScan() {
      if (timer) clearInterval(timer);
      timer = null;
      busy = false;
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
      }
      video.srcObject = null;
      scanBtn.disabled = false;
      stopBtn.disabled = true;
      setStatus('Stopped');
    }

    async function captureAndSend() {
      if (!stream || busy || video.videoWidth === 0) return;
      busy = true;
      setStatus('Processing', true);

      const maxWidth = 1280;
      const scale = Math.min(1, maxWidth / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(async blob => {
        if (!blob) {
          busy = false;
          return;
        }
        const form = new FormData();
        form.append('frame', blob, 'frame.jpg');
        try {
          const res = await fetch('/api/scan-frame', { method: 'POST', body: form });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          const text = data.text || '';
          output.textContent = text || 'No Braille detected';
          detectionsEl.textContent = data.detections || 0;
          confidenceEl.textContent = `${Math.round((data.confidence || 0) * 100)}%`;
          stableEl.textContent = data.stable ? 'Yes' : 'No';
          setStatus(data.stable ? 'Stable reading' : 'Scanning', true);
          if (autoSpeak.checked && data.stable && text && text !== lastSpoken) {
            lastSpoken = text;
            speak(text);
          }
        } catch (err) {
          setStatus('Backend error');
          output.textContent = 'Scanner error';
          document.getElementById('hint').textContent = err.message || String(err);
        } finally {
          busy = false;
        }
      }, 'image/jpeg', 0.82);
    }

    scanBtn.addEventListener('click', startScan);
    stopBtn.addEventListener('click', stopScan);
    speakBtn.addEventListener('click', () => speak(output.textContent));
  </script>
</body>
</html>
"""


def _decode_upload(file_bytes: bytes) -> np.ndarray:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Image frame is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image frame exceeds upload limit")
    arr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image frame")
    if frame.shape[0] * frame.shape[1] > MAX_IMAGE_PIXELS:
        raise HTTPException(status_code=413, detail="Decoded image dimensions exceed limit")
    return frame


def _prepare_model_frame(frame: np.ndarray, flip_horizontal: bool) -> np.ndarray:
    """Mirror reverse-side Braille before detection when scanner flipping is enabled."""
    return cv2.flip(frame, 1) if flip_horizontal else frame


def _correct_word(word: str) -> str:
    clean = word.lower().strip()
    if not clean:
        return clean
    if clean in EXACT_CORRECTIONS:
        return EXACT_CORRECTIONS[clean]
    if clean in KNOWN_WORDS:
        return clean
    # Only correct against a tiny domain lexicon at a high cutoff.
    match = get_close_matches(clean, KNOWN_WORDS, n=1, cutoff=0.82)
    if match:
        return match[0]
    if spell is not None and clean.isalpha() and len(clean) > 2 and clean not in spell:
        correction = spell.correction(clean)
        if correction:
            return correction
    return clean


def _correct_text(text: str) -> str:
    corrected_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip().lower()
        if not line:
            continue
        if line in EXACT_CORRECTIONS:
            corrected_lines.append(EXACT_CORRECTIONS[line])
            continue
        words = [_correct_word(word) for word in line.split()]
        corrected_lines.append(" ".join(words))
    return "\n".join(corrected_lines)


def _normalize_label(label: str) -> str:
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def _decode_labels(labels: list[str]) -> str:
    text: list[str] = []
    number_mode = False
    capital_next = False

    for raw_label in labels:
        label = _normalize_label(raw_label)
        if label in {"number_indicator", "number", "num", "numeric_indicator"}:
            number_mode = True
            continue
        if label in {"capital_indicator", "capital", "cap", "caps"}:
            capital_next = True
            continue
        if label in CELL_TEXT:
            token = CELL_TEXT[label]
            text.append(token)
            if token.isspace():
                number_mode = False
                capital_next = False
            continue

        token = label
        if len(token) == 1 and token.isalpha():
            if number_mode and token in NUMBER_MAP:
                text.append(NUMBER_MAP[token])
                continue
            if number_mode and token not in NUMBER_MAP:
                number_mode = False
            if capital_next:
                token = token.upper()
                capital_next = False
            text.append(token)
            continue

        # Unknown future labels should not crash live scanning. Keep them readable.
        if token:
            text.append(token.replace("_", ""))
        number_mode = False
        capital_next = False

    return "".join(text)


def _cluster_lines(dets: list[dict[str, float | str]]) -> list[list[dict[str, float | str]]]:
    if not dets:
        return []

    avg_height = float(np.mean([float(d["height"]) for d in dets]))
    eps = max(avg_height * 0.6, 4.0)
    lines: list[list[dict[str, float | str]]] = []

    for det in sorted(dets, key=lambda d: float(d["y_center"])):
        best_index = None
        best_distance = None
        for idx, line in enumerate(lines):
            line_center = float(np.median([float(item["y_center"]) for item in line]))
            distance = abs(float(det["y_center"]) - line_center)
            if distance <= eps and (best_distance is None or distance < best_distance):
                best_index = idx
                best_distance = distance
        if best_index is None:
            lines.append([det])
        else:
            lines[best_index].append(det)

    return sorted(lines, key=lambda line: float(np.median([float(d["y_center"]) for d in line])))


def _box_iou(left: dict[str, float | str], right: dict[str, float | str]) -> float:
    x1 = max(float(left["x1"]), float(right["x1"]))
    y1 = max(float(left["y1"]), float(right["y1"]))
    x2 = min(float(left["x2"]), float(right["x2"]))
    y2 = min(float(left["y2"]), float(right["y2"]))
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, float(left["x2"]) - float(left["x1"])) * max(
        0.0, float(left["y2"]) - float(left["y1"])
    )
    right_area = max(0.0, float(right["x2"]) - float(right["x1"])) * max(
        0.0, float(right["y2"]) - float(right["y1"])
    )
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def _deduplicate_detections(
    detections: list[dict[str, float | str]],
) -> list[dict[str, float | str]]:
    kept: list[dict[str, float | str]] = []
    for detection in sorted(detections, key=lambda item: float(item["confidence"]), reverse=True):
        if all(_box_iou(detection, existing) < DUPLICATE_IOU for existing in kept):
            kept.append(detection)
    return kept


def _insert_adaptive_spaces(line: list[dict[str, float | str]]) -> list[str]:
    sorted_line = sorted(line, key=lambda d: float(d["x_center"]))
    if not sorted_line:
        return []
    if len(sorted_line) == 1:
        return [str(sorted_line[0]["label"])]

    gaps = [
        float(sorted_line[i + 1]["x_center"]) - float(sorted_line[i]["x_center"])
        for i in range(len(sorted_line) - 1)
    ]
    widths = [float(d["width"]) for d in sorted_line]
    median_gap = float(np.median(gaps))
    median_width = float(np.median(widths))
    compact_gaps = [gap for gap in gaps if gap <= median_gap * 1.25]
    cell_gap = float(np.median(compact_gaps)) if compact_gaps else median_gap
    space_threshold = max(
        cell_gap * SPACE_GAP_MULTIPLIER,
        median_width * SPACE_WIDTH_MULTIPLIER,
    )

    labels = [str(sorted_line[0]["label"])]
    for idx, det in enumerate(sorted_line[1:], start=1):
        if gaps[idx - 1] > space_threshold:
            labels.append("space")
        labels.append(str(det["label"]))
    return labels


def _reading_order_adaptive(dets: list[dict[str, float | str]]) -> str:
    lines = _cluster_lines(dets)
    decoded_lines: list[str] = []
    for line in lines:
        labels = _insert_adaptive_spaces(line)
        decoded = _decode_labels(labels).strip()
        if decoded:
            decoded_lines.append(decoded)
    return "\n".join(decoded_lines)


def _text_overlap_ratio(left: str, right: str) -> float:
    normalized_left = "".join(ch for ch in left.lower() if ch.isalnum())
    normalized_right = "".join(ch for ch in right.lower() if ch.isalnum())
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _history_for_client(client_id: str | None) -> deque[str]:
    if not client_id:
        return deque(maxlen=HISTORY_SIZE)
    normalized = client_id.strip()[:128]
    if not normalized:
        return deque(maxlen=HISTORY_SIZE)
    with history_lock:
        if normalized not in client_histories and len(client_histories) >= 1024:
            client_histories.pop(next(iter(client_histories)))
        return client_histories.setdefault(normalized, deque(maxlen=HISTORY_SIZE))


def _stabilize_text(corrected: str, stabilization_history: deque[str]) -> tuple[str, bool]:
    if corrected:
        if stabilization_history:
            previous_text, _ = Counter(stabilization_history).most_common(1)[0]
            if previous_text and _text_overlap_ratio(corrected, previous_text) < 0.3:
                stabilization_history.clear()
        stabilization_history.append(corrected)
    if not stabilization_history:
        return corrected, False
    stable_text, votes = Counter(stabilization_history).most_common(1)[0]
    return stable_text, votes >= 2


def _predict(
    frame: np.ndarray,
    include_image: bool = False,
    flip_horizontal: bool | None = None,
    stabilization_history: deque[str] | None = None,
) -> dict[str, Any]:
    should_flip = FLIP_HORIZONTAL if flip_horizontal is None else flip_horizontal
    model_frame = _prepare_model_frame(frame, should_flip)

    def run_model(input_frame: np.ndarray):
        with predict_lock:
            return model.predict(
                input_frame,
                conf=CONFIDENCE,
                iou=IOU,
                imgsz=IMGSZ,
                verbose=False,
                augment=AUGMENT_INFERENCE,
                agnostic_nms=False,
            )[0]

    processed = preprocess(model_frame) if ENHANCE_IMAGE else model_frame
    result = run_model(processed)
    if ENHANCE_IMAGE and len(result.boxes) == 0:
        result = run_model(model_frame)

    dets = []
    annotated = frame.copy() if include_image else None
    frame_h, frame_w = frame.shape[:2]

    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        display_x1, display_x2 = (
            (frame_w - x2, frame_w - x1) if should_flip else (x1, x2)
        )
        label = names[int(box.cls[0])]
        conf = float(box.conf[0])
        dets.append(
            {
                "x_center": (display_x1 + display_x2) / 2,
                "y_center": (y1 + y2) / 2,
                "label": label,
                "width": x2 - x1,
                "height": y2 - y1,
                "confidence": conf,
                "x1": display_x1,
                "y1": y1,
                "x2": display_x2,
                "y2": y2,
            }
        )
    dets = _deduplicate_detections(dets)
    confidences = [float(det["confidence"]) for det in dets]
    boxes = []
    for det in dets:
        display_x1 = float(det["x1"])
        y1 = float(det["y1"])
        display_x2 = float(det["x2"])
        y2 = float(det["y2"])
        label = str(det["label"])
        conf = float(det["confidence"])
        boxes.append(
            {
                "label": label,
                "confidence": round(conf, 4),
                "x1": round(max(0.0, min(1.0, display_x1 / frame_w)), 5),
                "y1": round(max(0.0, min(1.0, y1 / frame_h)), 5),
                "x2": round(max(0.0, min(1.0, display_x2 / frame_w)), 5),
                "y2": round(max(0.0, min(1.0, y2 / frame_h)), 5),
            }
        )
        if annotated is not None:
            cv2.rectangle(
                annotated,
                (int(display_x1), int(y1)),
                (int(display_x2), int(y2)),
                (0, 230, 0),
                2,
            )
            cv2.putText(
                annotated,
                label,
                (int(display_x1), max(18, int(y1) - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 230, 0),
                2,
            )

    raw_text = _reading_order_adaptive(dets)
    corrected = _correct_text(raw_text)
    stable_text, stable = _stabilize_text(
        corrected,
        stabilization_history if stabilization_history is not None else deque(maxlen=HISTORY_SIZE),
    )

    payload: dict[str, Any] = {
        "ok": True,
        "text": stable_text or corrected,
        "stable": stable,
        "detections": len(dets),
        "confidence": round(float(np.mean(confidences)), 4) if confidences else 0.0,
        "raw_text": raw_text,
        "corrected_text": corrected,
        "boxes": boxes,
        "detector_classes": len(names),
        "supported_future_classes": FUTURE_CLASS_SCHEMA,
        "input_flipped_horizontal": should_flip,
    }

    if annotated is not None:
        ok, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            payload["annotated_image"] = base64.b64encode(buffer).decode("ascii")

    return payload


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return HTML


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "model": str(MODEL_PATH),
        "classes": len(names),
        "class_names": names,
        "future_class_schema": FUTURE_CLASS_SCHEMA,
        "confidence": CONFIDENCE,
        "iou": IOU,
        "duplicate_iou": DUPLICATE_IOU,
        "imgsz": IMGSZ,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_image_pixels": MAX_IMAGE_PIXELS,
        "flip_horizontal": FLIP_HORIZONTAL,
        "enhance_image": ENHANCE_IMAGE,
        "augment_inference": AUGMENT_INFERENCE,
        "space_gap_multiplier": SPACE_GAP_MULTIPLIER,
        "space_width_multiplier": SPACE_WIDTH_MULTIPLIER,
    }


@app.post("/api/scan-frame")
async def scan_frame(
    frame: UploadFile = File(...),
    include_image: bool = Query(default=False),
    flip_horizontal: bool | None = Query(default=None),
    client_id: str | None = Query(default=None),
) -> JSONResponse:
    if frame.content_type and not frame.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image frames are accepted")
    image = _decode_upload(await frame.read())
    return JSONResponse(
        await asyncio.to_thread(
            _predict,
            image,
            include_image,
            flip_horizontal,
            _history_for_client(client_id),
        )
    )


@app.websocket("/ws/scan")
async def scan_websocket(
    websocket: WebSocket,
    flip_horizontal: bool | None = Query(default=None),
) -> None:
    await websocket.accept()
    connection_history: deque[str] = deque(maxlen=HISTORY_SIZE)
    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            image = _decode_upload(frame_bytes)
            payload = await asyncio.to_thread(
                _predict,
                image,
                False,
                flip_horizontal,
                connection_history,
            )
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        return
    except HTTPException as exc:
        await websocket.send_json({"ok": False, "error": str(exc.detail)})
        await websocket.close(code=1003)
    except Exception as exc:
        del exc
        await websocket.send_json({"ok": False, "error": "Scanner processing failed"})
        await websocket.close(code=1011)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BRAILLE_HOST", "0.0.0.0")
    port = int(os.environ.get("BRAILLE_PORT", "8088"))
    uvicorn.run("scanner_api:app", host=host, port=port, reload=False)
