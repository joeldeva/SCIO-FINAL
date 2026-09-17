# SCIO-FINAL New Chat Handoff

This repository is the consolidated Sciobraille/BrailleVision workspace prepared from the local `BRAILLEVISION` folder.

It includes source code, datasets, trained models, model exports, Android app code, backend code, release artifacts, documentation, and reference projects.

## Main Product Folder

The current product is in `sciobraille-scanner`.

Important files and folders:

- `sciobraille-scanner/backend/scanner_api.py` - main FastAPI scanner backend.
- `sciobraille-scanner/backend/model/best.pt` - active production YOLOv8s model.
- `sciobraille-scanner/backend/model/best.onnx` - ONNX export.
- `sciobraille-scanner/backend/model/best_saved_model` - TFLite/SavedModel exports.
- `sciobraille-scanner/android` - native Android/Kotlin app.
- `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite` - offline Android fallback model.
- `sciobraille-scanner/releases` - debug APK, release AAB, and checksums.
- `sciobraille-scanner/docs` - Play Store, backend deployment, model expansion, privacy, and data safety docs.

## Scanner API

Run backend:

```powershell
cd sciobraille-scanner/backend
python scanner_api.py
```

Endpoints:

- `GET /api/health`
- `POST /api/scan-frame`
- `WS /ws/scan`

The backend flips uploaded/captured frames horizontally by default before model inference.

## Active Model

Active production model: `sciobraille-scanner/backend/model/best.pt`

Known details:

- YOLOv8s object detector
- 26 classes: `a-z`
- Input: 640x640 RGB
- Size: about 21.5 MB
- Parameters: about 11.1M
- Documented metrics: mAP50 93.15%, mAP50-95 72.36%, precision 95.72%, recall 90.85%

Limitation: it detects Grade 1 English letters only. It does not truly detect numbers, punctuation, capital indicators, spaces, or Grade 2 contractions yet.

## Reference Projects

### prabh-decoders-braillevision

Best source/reference project.

- `dataset/braille_merged` - strongest merged YOLO dataset: 1,614 images, 90,469 boxes, 26 classes.
- `model/best.pt` - older large Model A, strong on known Sciobraille test image.
- `model/best_B.pt` - duplicate of current production model.
- `merge_datasets.py` - dataset merge pipeline.
- `training` - Kaggle training scripts.

### sangam-Braillie

Large Roboflow/reference project.

- `dataset` - 2,062-image YOLO dataset.
- `model/best.pt` - 26-class model.
- `model/yolov8_braille.pt` - 64-class dot-pattern model, useful research direction.
- `model/best.onnx` - ONNX export.

### asmitha

Streamlit prototype and dataset.

- `dataset` - 1,325-image YOLO dataset.
- `app.py` - Streamlit app.
- `inference.py` - CLI inference.
- `runs/detect/braille_detector-4/weights/best.pt` - best local Asmitha model.

### braille_hackathon_siddhant

Reference web/backend prototype.

- `backend`
- `frontend`
- `model/best.pt`
- `tests`

## Datasets Not Fully Used In Active Model

The active production model mainly comes from the Prabh merged dataset. Useful datasets still available for future retraining:

- `asmitha/dataset`
- `sangam-Braillie/dataset`
- `braille_hackathon_siddhant/dataset`

Recommended next training step:

1. Merge `prabh + sangam + asmitha` datasets.
2. Normalize class names to lowercase `a-z`.
3. Deduplicate images by hash.
4. Add real phone-camera samples from the target use case.
5. Retrain a new YOLO model.
6. Compare against `sciobraille-scanner/backend/model/best.pt` on a fixed validation/test set.

## Push Staging Note

Regenerable build/cache folders were intentionally excluded from this push staging copy:

- Android `build/`
- Gradle `.gradle/`
- IDE `.idea/`
- Python `__pycache__/`
- pytest cache
- Kotlin build cache

Datasets, source code, models, docs, and release artifacts are included.

## Full File List

See `FULL_FILE_MANIFEST.txt`.
