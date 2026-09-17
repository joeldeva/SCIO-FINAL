"""
main.py — BrailleVision FastAPI (with live camera + enhanced detection)
=======================================================================
Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
  GET  /                  → serves static/index.html
  GET  /health            → model status check
  POST /predict           → standard image detection
  POST /predict/enhanced  → detection with contrast/sharpening preprocessing
  POST /predict_frame     → lightweight live webcam frame detection
"""
import base64
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import BrailleDetector

# ── Init ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="BrailleVision API")

try:
    detector = BrailleDetector(weights="model/best.pt", conf=0.25)
except SystemExit as e:
    print(f"[ERROR] Model load failed: {e}")
    detector = None

app.mount("/static", StaticFiles(directory="static"), name="static")


# ══════════════════════════════════════════════════════════════════════════════
# Helper: decode uploaded bytes → cv2 BGR frame
# ══════════════════════════════════════════════════════════════════════════════
def decode_image(contents: bytes) -> np.ndarray:
    np_arr = np.frombuffer(contents, np.uint8)
    frame  = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not decode image.")
    return frame


# ══════════════════════════════════════════════════════════════════════════════
# Helper: enhancement preprocessing pipeline
# ══════════════════════════════════════════════════════════════════════════════
def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Preprocessing pipeline to improve detection of embossed / low-contrast
    physical Braille dots before passing to YOLO.

    Pipeline (in order):
      1. Grayscale conversion   — strip colour noise, work in luminance only
      2. CLAHE                  — boost local contrast so dots pop
      3. Gaussian blur          — smooth surface texture noise
      4. Unsharp masking        — sharpen dot edges without amplifying noise
      5. Gamma correction       — pull up mid-tones to separate dots from bg
      6. Convert back to BGR    — YOLO expects 3-channel BGR input
    """

    # 1. Grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 2. CLAHE — clipLimit=3.0, 8×8 tiles (tuned for Braille cell density)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)

    # 3. Gaussian blur — mild 3×3 kernel removes grain, keeps dot edges
    blurred = cv2.GaussianBlur(gray, (3, 3), sigmaX=0)

    # 4. Unsharp masking — sharpen = original + weight*(original - heavy_blur)
    heavy_blur = cv2.GaussianBlur(gray, (9, 9), sigmaX=0)
    sharpened  = cv2.addWeighted(gray, 1.8, heavy_blur, -0.8, 0)

    # 5. Gamma correction (gamma < 1 brightens mid-tones → better dot separation)
    gamma = 0.75
    lut   = np.array(
        [min(255, int(((i / 255.0) ** gamma) * 255)) for i in range(256)],
        dtype=np.uint8,
    )
    corrected = cv2.LUT(sharpened, lut)

    # 6. Back to BGR for YOLO
    return cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)


# ══════════════════════════════════════════════════════════════════════════════
# Helper: run YOLO inference and build response dict
# ══════════════════════════════════════════════════════════════════════════════
def run_inference(frame: np.ndarray, enhanced_b64: str = None) -> dict:
    """
    Run BrailleDetector on *frame* and return a standardised result dict.

    Args:
        frame        : BGR image (numpy array) to run inference on.
        enhanced_b64 : optional base64 JPEG of the preprocessed image;
                       when provided it is added to the response as
                       'enhanced_image_b64' so the frontend can display it.

    Returns:
        dict with keys: success, text, letters, count, inference_ms,
                        image_b64, [enhanced_image_b64]
    """
    if detector is None:
        raise HTTPException(500, "Model not loaded — check model/best.pt exists.")

    try:
        t0 = time.perf_counter()
        results, text, dets = detector.predict_frame(frame)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:
        raise HTTPException(500, f"Inference failed: {str(e)}")

    # Annotated result image → base64
    annotated = results[0].plot()
    _, buffer  = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64    = base64.b64encode(buffer).decode("utf-8")

    # Per-letter breakdown
    letters = [
        {"letter": d["label"], "confidence": round(d["conf"] * 100, 1)}
        for d in dets
    ]

    payload = {
        "success":      True,
        "text":         text if text else "No Braille detected",
        "letters":      letters,
        "count":        len(dets),
        "inference_ms": elapsed_ms,
        "image_b64":    img_b64,
    }

    # Only present in /predict/enhanced responses
    if enhanced_b64 is not None:
        payload["enhanced_image_b64"] = enhanced_b64

    return payload


# ══════════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    return Path("static/index.html").read_text(encoding="utf-8")


@app.get("/health")
async def health():
    """Quick liveness / model-loaded check."""
    return {"status": "ok", "model_loaded": detector is not None}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Standard detection.
    Raw image is passed directly to YOLO with no preprocessing.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files accepted.")
    frame = decode_image(await file.read())
    return JSONResponse(run_inference(frame))


@app.post("/predict/enhanced")
async def predict_enhanced(file: UploadFile = File(...)):
    """
    Enhanced detection.
    Applies the contrast / sharpening pipeline (enhance_frame) before YOLO.
    Useful for embossed, low-contrast, or poorly-lit Braille images.

    Extra response field:
      enhanced_image_b64 — base64 JPEG of the preprocessed image so the
                           frontend can show what the model actually saw.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files accepted.")

    frame    = decode_image(await file.read())
    enhanced = enhance_frame(frame)

    # Encode the preprocessed image for frontend preview
    _, enc_buf   = cv2.imencode(".jpg", enhanced, [cv2.IMWRITE_JPEG_QUALITY, 90])
    enhanced_b64 = base64.b64encode(enc_buf).decode("utf-8")

    return JSONResponse(run_inference(enhanced, enhanced_b64=enhanced_b64))


@app.post("/predict_frame")
async def predict_frame_endpoint(file: UploadFile = File(...)):
    """
    Live webcam frame endpoint.
    Called repeatedly by the browser (~every 600 ms) during camera mode.
    Returns a lighter response — no per-letter breakdown — to keep latency low.
    """
    frame = decode_image(await file.read())
    data  = run_inference(frame)
    return JSONResponse({
        "success":      data["success"],
        "text":         data["text"],
        "count":        data["count"],
        "inference_ms": data["inference_ms"],
        "image_b64":    data["image_b64"],
    })