# Model Information

## Deployed Model: Sciobraille V2 Master

- **File:** `best.pt` (22,516,906 bytes)
- **SHA-256:** `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62`
- **Architecture:** YOLOv8s
- **Input:** 640 x 640 RGB
- **Classes:** 26 (`a` through `z`)
- **Training:** 30 epochs, AdamW, seed 20260923
- **Dataset:** Master V2, 1,784 images and 99,352 bounding boxes
- **Runtime:** confidence 0.25, IoU 0.45, duplicate IoU 0.70, horizontal flip enabled
- **Previous V1 PT rollback:** `best_previous_B.pt`
- **Previous V1 Android rollback:** `best_saved_model/best_int8.tflite`

### Internal Test Metrics

| Metric | Value |
|---|---:|
| mAP50 | 95.35% |
| mAP50-95 | 79.24% |
| Precision | 96.85% |
| Recall | 93.39% |

Accuracy metrics above use Master V2 internal test data. Physical-image text accuracy must use `raw_text`, never corrected text.

## Runtime Artifacts

| Target | Path | SHA-256 |
|---|---|---|
| Backend PyTorch | `model/best.pt` | `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62` |
| Android INT8 | `../../android/app/src/main/assets/best_int8.tflite` | `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c` |
| V1 rollback | `model/best_previous_B.pt` | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |

## Usage

```bash
python scanner_api.py
```

See `rollback/v2_promotion_20260925.json` for exact promotion and rollback metadata.
