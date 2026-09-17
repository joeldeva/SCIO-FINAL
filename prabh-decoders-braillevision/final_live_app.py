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
import os
import threading
from collections import Counter, deque
from difflib import get_close_matches
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from ultralytics import YOLO

from inference import preprocess, reading_order


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", BASE_DIR / "model" / "best.pt"))
CONFIDENCE = float(os.environ.get("BRAILLE_CONF", "0.35"))
IMGSZ = int(os.environ.get("BRAILLE_IMGSZ", "640"))
HISTORY_SIZE = int(os.environ.get("BRAILLE_HISTORY", "5"))

app = FastAPI(title="BrailleVision Final Live Scanner")
model = YOLO(str(MODEL_PATH))
names = model.names
predict_lock = threading.Lock()
history: deque[str] = deque(maxlen=HISTORY_SIZE)


KNOWN_WORDS = [
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
  <title>BrailleVision Live Scanner</title>
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
        <h1>BrailleVision Live</h1>
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
    arr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image frame")
    return frame


def _correct_word(word: str) -> str:
    clean = word.lower().strip()
    if not clean:
        return clean
    if clean in EXACT_CORRECTIONS:
        return EXACT_CORRECTIONS[clean]
    # Only correct against a tiny domain lexicon at a high cutoff.
    match = get_close_matches(clean, KNOWN_WORDS, n=1, cutoff=0.82)
    return match[0] if match else clean


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


def _predict(frame: np.ndarray, include_image: bool = False) -> dict[str, Any]:
    processed = preprocess(frame)
    with predict_lock:
        result = model.predict(
            processed,
            conf=CONFIDENCE,
            imgsz=IMGSZ,
            verbose=False,
            augment=False,
        )[0]

    dets = []
    confidences = []
    annotated = frame.copy() if include_image else None

    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        label = names[int(box.cls[0])]
        conf = float(box.conf[0])
        dets.append(((x1 + x2) / 2, (y1 + y2) / 2, label, y2 - y1))
        confidences.append(conf)
        if annotated is not None:
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 230, 0), 2)
            cv2.putText(
                annotated,
                label,
                (int(x1), max(18, int(y1) - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 230, 0),
                2,
            )

    raw_text = reading_order(dets)
    corrected = _correct_text(raw_text)
    if corrected:
        history.append(corrected)

    stable_text = corrected
    stable = False
    if history:
        stable_text, votes = Counter(history).most_common(1)[0]
        stable = votes >= 2

    payload: dict[str, Any] = {
        "text": stable_text or corrected,
        "stable": stable,
        "detections": len(dets),
        "confidence": round(float(np.mean(confidences)), 4) if confidences else 0.0,
        "raw_text": raw_text,
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
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": str(MODEL_PATH),
        "classes": len(names),
        "confidence": CONFIDENCE,
        "imgsz": IMGSZ,
    }


@app.post("/api/scan-frame")
async def scan_frame(
    frame: UploadFile = File(...),
    include_image: bool = Query(default=False),
) -> JSONResponse:
    if frame.content_type and not frame.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image frames are accepted")
    image = _decode_upload(await frame.read())
    return JSONResponse(_predict(image, include_image=include_image))


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BRAILLE_HOST", "0.0.0.0")
    port = int(os.environ.get("BRAILLE_PORT", "8088"))
    uvicorn.run("final_live_app:app", host=host, port=port, reload=False)
