# Model Information

## Weights Access
The trained YOLO model weights are included in this repository at `model/best.pt`.

- **File:** `model/best.pt`
- **Format:** PyTorch `.pt`
- **Architecture:** YOLOv8-nano (yolov8n)
- **Task:** Object Detection (Braille character classification)
- **Classes:** 26 (a–z)
- **Input Size:** 1280x720

## How to Load the Model
```python
from ultralytics import YOLO
model = YOLO('model/best.pt')
results = model('sample_inputs/test_braille.jpg')
```

## Quick Inference Command
```bash
python inference/inference.py --source sample_inputs/test_braille.jpg --weights model/best.pt
```
