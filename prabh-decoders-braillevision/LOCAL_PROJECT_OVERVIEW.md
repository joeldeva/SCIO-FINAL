# Local Project Overview

This folder is a local copy of `prabh505/the-decoders-braillevision`.

## What Is Available Locally

- Source code: `inference.py`, `app.py`, `app_web.py`, `api_server.py`
- Models: `model/best.pt`, `model/best_A.pt`, `model/best_B.pt`, `model/best_C.pt`
- Android APK: `BrailleVision.apk`
- Flutter app source: `flutter_app/`
- Sample inputs and outputs: `sample_inputs/`, `sample_outputs/`
- Full merged dataset: `dataset/braille_merged/`
- Original dataset zip backup: `local_archives/braille_merged_archive.zip`
- Training scripts: `training/train_kaggle.py`, `training/train_kaggle_v11.py`
- Documentation: `README.md`, `docs/`, `dataset/dataset_info.md`, `model/model_info.md`

## Dataset

The extracted dataset is in YOLO format:

- Train images: 1372
- Val images: 242
- Train labels: 1372
- Val labels: 242
- Classes: 26 letters, `a` through `z`

Local dataset config:

`dataset/braille_merged/data.yaml`

## Running

Final live scanner:

```bash
python final_live_app.py
```

Open `http://127.0.0.1:8088` on the laptop. On the same Wi-Fi, open
`http://<laptop-ip>:8088` from another device. Phone browsers may require
HTTPS for camera access.

Offline inference:

```bash
python inference.py --source sample_inputs/ --weights model/best.pt
```

Web app:

```bash
python app_web.py
```

Phone URL on the current Wi-Fi was:

`http://192.168.1.3:7860`

## Keys And External Dependencies

No real API keys are stored in this project. Roboflow/Kaggle references are only needed if re-downloading or retraining from external sources. The code, trained models, APK, and merged dataset are now available locally.
