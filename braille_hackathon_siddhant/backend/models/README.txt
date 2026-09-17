Place your trained YOLOv8 model weights here.

Expected filename: best.pt

How to get best.pt:
1. Run the training notebook: training/braille_train.ipynb (Google Colab)
2. Download the generated best.pt
3. Place it in this folder: backend/models/best.pt

The system will automatically detect and load the model on startup.
If best.pt is not present, the system falls back to classical OpenCV-based detection.

Model format: YOLOv8 PyTorch (.pt)
Alternative formats also supported: .onnx, .tflite
