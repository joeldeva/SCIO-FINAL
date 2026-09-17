# Setup & Run Instructions

## 1. Clone & install (Python)
```bash
git clone <YOUR REPO URL>
cd <repo>
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Verify the model on a sample image (what judges run)
```bash
python inference.py --source sample_inputs/test_braille.jpg --weights model/best.pt
# or a whole folder:
python inference.py --source sample_inputs/ --weights model/best.pt
```
Outputs (annotated image + decoded `.txt`) land in `sample_outputs/`.

## 3. Reproduce metrics (optional)
```bash
python evaluate.py model/best.pt     # needs test/ images + test/labels.csv
```

## 4. Desktop live demo (optional)
```bash
python app.py --weights model/best.pt        # q quit · s speak · space pause
```

## 5. Web app (optional fallback)
```bash
python app_web.py                              # opens http://localhost:7860
```

## 6. Android APK
- Install the prebuilt APK from the GitHub Release, **or**
- Build it yourself: follow `FLUTTER_APK_SETUP.md` (clone the Ultralytics example app, drop in `model/best.tflite`, `flutter build apk --release`).

## Requirements
- Python 3.9–3.12, pip.
- For the APK build: Flutter SDK + Android SDK (`flutter doctor`).
- A camera (webcam or phone) for the live demos; sample images need no camera.
