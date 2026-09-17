#!/usr/bin/env python3
"""
BrailleVision -- API Server for Flutter App

Runs a Flask server that accepts camera frames and returns YOLO detections.
The Flutter app sends images via HTTP POST, this server runs inference
with bilateral filter + TTA, and returns annotated image + decoded text.

Run:
    python api_server.py
    # Starts on http://0.0.0.0:5000

The Flutter app should be configured to point to your laptop's IP:
    http://<your-laptop-ip>:5000
"""

import base64
import io
import os

import cv2
import numpy as np
from flask import Flask, request, jsonify
from ultralytics import YOLO

MODEL_PATH = os.environ.get("MODEL_PATH", "model/best.pt")
model = YOLO(MODEL_PATH)
names = model.names

app = Flask(__name__)


def reading_order(dets, line_tol_frac=0.6, space_mult=1.7):
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
        s = ln[0][2]
        for prev, d in zip(ln, ln[1:]):
            if (d[0] - prev[0]) > med_h * space_mult:
                s += " "
            s += d[2]
        out.append(s)
    return "\n".join(out)


@app.route("/detect", methods=["POST"])
def detect():
    """Accept an image, run YOLO detection, return results."""
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    img_bytes = file.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Could not decode image"}), 400

    # Bilateral filter + TTA for best accuracy
    enhanced = cv2.bilateralFilter(img, 9, 75, 75)
    res = model.predict(enhanced, conf=0.35, verbose=False, augment=True)[0]

    # Extract detections
    annotated = img.copy()
    dets = []
    for b in res.boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        label = names[int(b.cls[0])]
        conf = float(b.conf[0])
        dets.append(((x1 + x2) / 2, (y1 + y2) / 2, label, y2 - y1))
        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 230, 0), 2)
        cv2.putText(annotated, f"{label}", (int(x1), int(y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)

    text = reading_order(dets)

    # Encode annotated image as base64
    _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    img_b64 = base64.b64encode(buffer).decode("utf-8")

    return jsonify({
        "text": text,
        "num_detections": len(dets),
        "annotated_image": img_b64,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_PATH, "classes": len(names)})


if __name__ == "__main__":
    print(f"\n🔥 BrailleVision API Server")
    print(f"   Model: {MODEL_PATH}")
    print(f"   Classes: {len(names)}")
    print(f"\n   Flutter app should connect to: http://<your-ip>:5000")
    print(f"   Test: curl http://localhost:5000/health\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
