#!/usr/bin/env python3
"""
BrailleVision -- Web App (Gradio)

Two modes:
  1. Upload an image  → get annotated result + decoded text + speak
  2. Live webcam stream → real-time detection + decoded text + speak

Run:
    python app_web.py
    # Opens at http://localhost:7860
"""

import os
import tempfile
from collections import deque, Counter

import cv2
import numpy as np
import gradio as gr
from ultralytics import YOLO
from gtts import gTTS

MODEL_PATH = os.environ.get("MODEL_PATH", "model/best.pt")
model = YOLO(MODEL_PATH)
names = model.names
_hist = deque(maxlen=5)


def reading_order(dets, line_tol_frac=0.6, space_mult=1.7):
    """dets: list of (cx, cy, label, box_height) -> text in reading order."""
    if not dets:
        return ""
    med_h = float(np.median([d[3] for d in dets]))
    dets = sorted(dets, key=lambda d: d[1])
    lines, cur = [], [dets[0]]
    for d in dets[1:]:
        if abs(d[1] - cur[-1][1]) <= med_h * line_tol_frac:
            cur.append(d)
        else:
            lines.append(cur)
            cur = [d]
    lines.append(cur)
    out = []
    for ln in lines:
        ln = sorted(ln, key=lambda d: d[0])
        text = ln[0][2]
        for prev, d in zip(ln, ln[1:]):
            if (d[0] - prev[0]) > med_h * space_mult:
                text += " "
            text += d[2]
        out.append(text)
    return "\n".join(out)


def detect_and_annotate(img_rgb, conf=0.35, use_tta=True):
    """Run YOLO on an RGB image, return annotated image + text.
    Applies bilateral filter preprocessing and optional TTA for best accuracy.
    """
    if img_rgb is None:
        return None, ""
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    # Bilateral filter: smooths paper texture while preserving dot edges
    enhanced = cv2.bilateralFilter(bgr, 9, 75, 75)
    res = model.predict(enhanced, conf=conf, verbose=False, augment=use_tta)[0]
    annotated = img_rgb.copy()
    dets = []
    for b in res.boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        label = names[int(b.cls[0])]
        dets.append(((x1 + x2) / 2, (y1 + y2) / 2, label, y2 - y1))
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 230, 0), 2)
        cv2.putText(annotated, label, (int(x1), int(y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)
    return annotated, reading_order(dets)


def process_upload(img_rgb):
    """Process a single uploaded image — uses TTA for best accuracy."""
    if img_rgb is None:
        return None, ""
    annotated, text = detect_and_annotate(img_rgb, 0.35, use_tta=True)
    return annotated, text


def process_webcam(frame_rgb):
    """Process a webcam frame — skips TTA for speed, uses temporal smoothing."""
    if frame_rgb is None:
        return None, ""
    annotated, text = detect_and_annotate(frame_rgb, 0.35, use_tta=False)
    _hist.append(text)
    stable = Counter(_hist).most_common(1)[0][0] if _hist else ""
    return annotated, stable


def speak(text):
    """Turn the current reading into speech via gTTS."""
    if not text or not text.strip():
        return None
    f = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    gTTS(text.replace("\n", ". ")).save(f.name)
    return f.name


# ---- Build the UI ----
with gr.Blocks(title="BrailleVision") as demo:
    gr.Markdown(
        "# 👁️ BrailleVision\n"
        "Detect and read Braille from images or live camera. "
        "**93% accuracy** across 26 letter classes (a–z).\n\n"
        "*Team: The Decoders*"
    )

    with gr.Tab("📤 Upload Image"):
        gr.Markdown("Upload a photo of Braille text to detect and decode it.")
        with gr.Row():
            upload_img = gr.Image(
                sources=["upload", "clipboard"],
                type="numpy",
                label="Upload Braille Image"
            )
            upload_out = gr.Image(type="numpy", label="Detected Braille Cells")
        upload_text = gr.Textbox(label="Decoded Reading", lines=3)
        with gr.Row():
            upload_btn = gr.Button("🔍 Detect Braille", variant="primary", size="lg")
            upload_speak = gr.Button("🔊 Speak", size="lg")
        upload_audio = gr.Audio(label="Speech", autoplay=True)

        upload_btn.click(
            process_upload,
            inputs=[upload_img],
            outputs=[upload_out, upload_text]
        )
        upload_speak.click(speak, inputs=upload_text, outputs=upload_audio)

    with gr.Tab("📷 Live Camera"):
        gr.Markdown("Point your camera at Braille text for real-time detection.")
        with gr.Row():
            cam = gr.Image(sources=["webcam"], streaming=True, type="numpy", label="Camera")
            cam_out = gr.Image(type="numpy", label="Detected Cells")
        cam_text = gr.Textbox(label="Live Reading", lines=2)
        with gr.Row():
            cam_speak = gr.Button("🔊 Speak", variant="primary")
            cam_clear = gr.Button("Clear")
        cam_audio = gr.Audio(label="Speech", autoplay=True)

        cam.stream(
            process_webcam,
            inputs=[cam],
            outputs=[cam_out, cam_text],
            stream_every=0.2,
            time_limit=600
        )
        cam_speak.click(speak, inputs=cam_text, outputs=cam_audio)
        cam_clear.click(lambda: (_hist.clear(), "")[1], outputs=cam_text)

    gr.Markdown(
        "---\n"
        "**Model:** YOLOv8s • **mAP@50:** 93.15% • **Classes:** 26 (a–z) • "
        "[GitHub](https://github.com/prabh505/the-decoders-braillevision)"
    )

if __name__ == "__main__":
    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    share = os.environ.get("GRADIO_SHARE", "").lower() in {"1", "true", "yes"}
    demo.launch(server_name=server_name, server_port=server_port, share=share)
