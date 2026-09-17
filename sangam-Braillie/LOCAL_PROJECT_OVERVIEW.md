# Local Project Overview

This folder is a local copy of `SangamNirala/Braillie` branch `main1`.

## What Is Available Locally

- Source code: `app.py`, `main.py`, `inference/predict.py`
- Frontend: `static/index.html`
- Training script: `training/train.py`
- Colab notebook from repo: `Google Colab/Braillie (1).ipynb`
- Attached notebook copy: `local_attachments/Braillie_1_attached.ipynb`
- Attached PDF documentation: `local_attachments/braillevision_project_documentation_RAJKUMAR_NIRALA.pdf`
- Models:
  - `model/best.pt`
  - `model/yolov8_braille.pt`
  - `model/best.onnx`
- Dataset: `dataset/`
- Training outputs: `runs/`
- Sample inputs: `sample_input/`
- Local test outputs generated during inspection:
  - `sample_outputs_test/`
  - `sample_outputs_fast/`
  - `sample_outputs_judge/`
  - `sample_outputs_judge_onnx/`

## Dataset

The dataset is Roboflow YOLOv8 format.

- Train images: 1757
- Validation images: 206
- Test images: 99
- Total images: 2062
- Classes: 26 uppercase Braille letters, `A` through `Z`

Dataset config:

`dataset/data.yaml`

Roboflow source recorded in the repo:

`https://universe.roboflow.com/sangam-nirala/braillify-evsdf/dataset/1`

The README also references:

`https://universe.roboflow.com/nicco-van-hamja-b1vxy/braillify`

## Model Notes

The shipped detector is a clean 26-class YOLO detector. Training report claims:

- Phase 2 mAP50: 0.9798
- Phase 2 mAP50-95: 0.7706
- Precision: 0.9426
- Recall: 0.976
- Weak classes: `F`, `J`

On the shared `judge_test.png`, this project detected many cells but decoded worse than `prabh-decoders-braillevision`, so keep it as a strong secondary project and model/training reference.

## Running

Batch inference:

```bash
python inference/predict.py --source sample_input --weights model/best.pt --output-dir sample_outputs_test --conf 0.25
```

FastAPI app:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Keys And External Dependencies

No real API keys were found. Google Drive paths in `training/train.py` are Colab backup paths, not secrets.

`requirements.txt` omits FastAPI/Uvicorn even though `main.py` uses them. They are installed on this laptop from earlier work.
