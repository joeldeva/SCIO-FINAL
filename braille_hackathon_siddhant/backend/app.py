"""
BrailleVision - FastAPI Backend
Real-time Braille detection and text-to-speech conversion API.
"""

import io
import os
import sys
import base64
import tempfile
import asyncio
import json
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# TTS
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from inference import run_inference, draw_results, preprocess_image
from braille_decoder import get_all_patterns, decode_sequence


# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="BrailleVision API",
    description="Real-time Braille detection and text-to-speech API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
    slow: bool = False


class ManualDecodeRequest(BaseModel):
    cells: list  # list of lists of dot positions


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    from inference import _yolo_model
    return {
        "status": "ok",
        "version": "1.0.0",
        "yolo_available": _yolo_model is not None,
        "model_loaded": _yolo_model is not None,
        "model_path": "backend/models/best.pt",
        "gtts_available": GTTS_AVAILABLE,
        "pyttsx3_available": PYTTSX3_AVAILABLE,
    }


# ─────────────────────────────────────────────
# Braille Reference
# ─────────────────────────────────────────────

@app.get("/braille/reference")
async def braille_reference():
    """Return all Braille alphabet patterns for the reference chart."""
    return {"patterns": get_all_patterns()}


# ─────────────────────────────────────────────
# Main Detection Endpoint
# ─────────────────────────────────────────────

@app.post("/detect")
async def detect_braille(file: UploadFile = File(...)):
    """
    Accept an image upload, run Braille detection, return decoded text + metadata.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=422, detail="Could not decode image")

    # Run inference
    result = run_inference(image)

    # Draw annotated image
    annotated = draw_results(image, result)
    _, buf = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    annotated_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')

    # Preprocessed (for debugging)
    preprocessed = preprocess_image(image)
    preprocessed_bgr = cv2.cvtColor(preprocessed, cv2.COLOR_GRAY2BGR)
    _, pbuf = cv2.imencode('.jpg', preprocessed_bgr)
    preprocessed_b64 = base64.b64encode(pbuf.tobytes()).decode('utf-8')

    return {
        "success": True,
        "text": result["text"],
        "confidence": result["confidence"],
        "method": result["method"],
        "cells_detected": result["cells_detected"],
        "dots_detected": result["dots_detected"],
        "cells": result["cells"],
        "annotated_image": annotated_b64,
        "preprocessed_image": preprocessed_b64,
    }


# ─────────────────────────────────────────────
# Manual Decode (dot patterns → text)
# ─────────────────────────────────────────────

@app.post("/decode")
async def manual_decode(req: ManualDecodeRequest):
    """Decode a list of Braille cell dot patterns into text."""
    text = decode_sequence(req.cells)
    return {"text": text, "cell_count": len(req.cells)}


# ─────────────────────────────────────────────
# Text-to-Speech
# ─────────────────────────────────────────────

@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Convert text to speech, return base64-encoded MP3."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Clean up text for TTS engine (newlines and question marks cause skips)
    text = req.text[:500].replace('\n', ' ').replace('\r', ' ').replace('?', ' ')

    if GTTS_AVAILABLE:
        try:
            tts = gTTS(text=text, lang=req.lang, slow=req.slow)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode('utf-8')
            return {"audio": audio_b64, "engine": "gtts"}
        except Exception as e:
            pass  # fall through to pyttsx3

    if PYTTSX3_AVAILABLE:
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp_path = tmp.name
            engine = pyttsx3.init()
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            with open(tmp_path, 'rb') as f:
                audio_b64 = base64.b64encode(f.read()).decode('utf-8')
            os.unlink(tmp_path)
            return {"audio": audio_b64, "engine": "pyttsx3"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

    raise HTTPException(
        status_code=503,
        detail="No TTS engine available. Install gtts: pip install gtts"
    )


@app.get("/tts")
async def text_to_speech_get(text: str, lang: str = "en"):
    """GET version for easy browser testing."""
    return await text_to_speech(TTSRequest(text=text, lang=lang))


# ─────────────────────────────────────────────
# WebSocket Live Stream
# ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for live camera processing.
    Client sends base64-encoded JPEG frames, server returns detection results.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            try:
                payload = json.loads(data)
                frame_b64 = payload.get("frame", "")

                if not frame_b64:
                    continue

                # Decode base64 frame
                if "," in frame_b64:
                    frame_b64 = frame_b64.split(",")[1]

                frame_bytes = base64.b64decode(frame_b64)
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                # Run inference
                result = run_inference(frame)

                # Draw and encode result
                annotated = draw_results(frame, result)
                _, buf = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                annotated_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')

                response = {
                    "text": result["text"],
                    "confidence": result["confidence"],
                    "cells_detected": result["cells_detected"],
                    "method": result["method"],
                    "annotated_frame": f"data:image/jpeg;base64,{annotated_b64}",
                }

                await websocket.send_text(json.dumps(response))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
            except Exception as e:
                await websocket.send_text(json.dumps({"error": str(e)}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
