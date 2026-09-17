# Offline Fallback

The app primarily uses the backend WebSocket scanner because the backend has the
most reliable Python/OpenCV/YOLO pipeline.

For demo resilience, the Android app now also packages:

```text
android/app/src/main/assets/best_int8.tflite
```

This model was exported from:

```text
backend/model/best.pt
```

Export command:

```python
from ultralytics import YOLO
model = YOLO("backend/model/best.pt")
model.export(format="tflite", int8=True, imgsz=640)
```

When the WebSocket backend is unavailable, the Android app attempts local TFLite
inference and displays a fallback result. This is a safety net, not the primary
production path.

Important limitations:

- The fallback uses the same 26-class `a-z` model.
- It does not include the full Python preprocessing pipeline.
- It should be validated on real phone hardware before relying on it for Play
  Store quality.
- A future on-device model should be retrained with the expanded class set in
  `MODEL_CLASS_EXPANSION.md`.
