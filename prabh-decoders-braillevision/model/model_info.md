# Model Information

## Deployed Model: Model B (YOLOv8s)
- **File:** `best.pt` (21MB)
- **Architecture:** YOLOv8s (small, 11.2M parameters)
- **Input:** 640×640 RGB
- **Classes:** 26 (a-z English Braille letters)
- **Training:** 150 epochs, AdamW optimizer, heavy augmentation
- **Dataset:** 1,614 images / 90,469 bounding boxes (merged from Roboflow + Angelina)

### Metrics
| Metric | Value |
|--------|-------|
| mAP@50 | 93.15% |
| mAP@50-95 | 72.36% |
| Precision | 95.72% |
| Recall | 90.85% |

## All Models Compared

| Model | Architecture | mAP@50 | Size | File |
|-------|-------------|--------|------|------|
| A (DotNeuralNet transfer) | YOLOv8 + pretrained braille backbone | 92.88% | 50MB | best_A.pt |
| **B (Primary)** | **YOLOv8s** | **93.15%** | **21MB** | **best.pt** |
| C (Latest gen) | YOLOv11n | 89.29% | 5.2MB | best_C.pt |

## Usage
```bash
python inference.py --source image.jpg --weights model/best.pt
python app.py --weights model/best.pt        # live webcam
python app_web.py                             # web browser
```

## Training Reproduction
See `training/train_kaggle.py` for Model A/B and `training/train_kaggle_v11.py` for Model C.

Upload `braille_merged.zip` to Kaggle, paste the script, and run on GPU T4.
