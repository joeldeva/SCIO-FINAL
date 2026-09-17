# Asmitha BrailleVision Local Snapshot

This folder is a standalone local copy of the `techAsmita/BrailleVision` project.
It does not depend on the GitHub repo to run.

## Purpose

Real-time or uploaded-image physical Braille detection using YOLOv8, OpenCV, and Streamlit.

## Main Files

- `app.py` - Streamlit web app.
- `inference.py` - command-line inference on one image.
- `train.py` - YOLOv8 training script.
- `requirements.txt` - Python dependencies.
- `dataset/` - local YOLO dataset with images, labels, and `data.yaml`.
- `runs/detect/braille_detector-4/weights/best.pt` - trained YOLO model.
- `sample_inputs/` - test images.
- `sample_outputs/` - reference outputs/screenshots.

## Model

Model path:

```text
runs/detect/braille_detector-4/weights/best.pt
```

Classes:

```text
A-Z
```

## Dataset

Local dataset path:

```text
dataset/
```

Dataset summary:

```text
train: 1016 images
valid: 209 images
test: 100 images
classes: 26 A-Z
```

## Run App

```powershell
cd C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\asmitha
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Laptop URL:

```text
http://localhost:8501
```

Phone URL on same Wi-Fi:

```text
http://192.168.1.3:8501
```

On phone, use `Phone snapshot / upload`, then `Browse files -> Camera -> Take photo`.
Direct camera capture may be blocked by mobile browsers on non-HTTPS local IP pages.

## Run CLI Inference

```powershell
python inference.py sample_inputs\1097_jpg.rf.6774c7b6f4e66bb1adcc86273677b34e.jpg
```

## Notes

The original Streamlit webcam mode uses the laptop/server webcam via `cv2.VideoCapture(0)`.
It does not stream the phone camera. The local `app.py` was patched to add a phone snapshot/upload mode.
