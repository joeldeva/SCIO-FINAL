# BrailleVision — Flutter APK Build Guide

## Prerequisites

- Flutter SDK 3.19+ installed
- Android SDK with API 34
- ADB for device testing
- Trained model exported as TFLite (`best_B.tflite` or `best_C.tflite`)

## Quick Build (5 minutes)

### Step 1: Clone the Ultralytics YOLO Flutter template

```bash
git clone https://github.com/ultralytics/yolo-flutter-app.git
cd yolo-flutter-app
```

### Step 2: Copy BrailleVision files

```bash
# Copy our custom screen
cp ../braillevision/flutter_app/lib/main.dart lib/main.dart
cp ../braillevision/flutter_app/lib/braille_screen.dart lib/braille_screen.dart

# Copy TFLite model to assets
mkdir -p android/app/src/main/assets
cp ../braillevision/model/best_C.tflite android/app/src/main/assets/best.tflite
```

> **Why Model C?** At 5.2MB it's ideal for mobile. Model B (21MB) also works but is larger.

### Step 3: Add dependencies

Add these to `pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  ultralytics_yolo: ^0.0.4
  flutter_tts: ^4.0.2
```

### Step 4: Build APK

```bash
flutter pub get
flutter build apk --release
```

APK will be at: `build/app/outputs/flutter-apk/app-release.apk`

### Step 5: Install on device

```bash
adb install build/app/outputs/flutter-apk/app-release.apk
```

## What the App Does

1. Opens phone camera in fullscreen
2. Runs YOLO detection on each frame (on-device, no internet needed)
3. Draws bounding boxes around detected Braille cells
4. Shows decoded text at bottom of screen
5. Auto-speaks the reading via TTS
6. Buttons: **Speak** (re-read) and **Clear** (reset)

## Generating TFLite from .pt

If you only have the PyTorch weights:

```python
from ultralytics import YOLO
model = YOLO("model/best.pt")  # or best_C.pt
model.export(format="tflite", int8=True, imgsz=640)
```

This creates `best_saved_model/best_int8.tflite` — rename to `best.tflite` and copy to assets.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Camera black screen | Grant camera permission in Android settings |
| Model not loading | Ensure `best.tflite` is in `android/app/src/main/assets/` |
| Out of memory | Use Model C (5.2MB) instead of Model B |
| Slow detection | Reduce image size: change `imgsz` in export to 320 |
