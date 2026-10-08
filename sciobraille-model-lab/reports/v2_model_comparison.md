# Sciobraille V2 Model Comparison (Candidate A vs Candidate B)

Comparative evaluation of V2 candidate architectures trained on Master V2 under identical conditions.

## Candidate Configurations

1. **Candidate A (YOLOv8s):** Initialized from production Model B weights (`sciobraille-scanner/backend/model/best.pt`).
2. **Candidate B (YOLO11s):** Initialized from official pre-trained COCO weights (`yolo11s.pt`).

## Validation Metrics (Master V2 Validation Split: 165 images)

| Metric | Candidate A (YOLOv8s) | Candidate B (YOLO11s) | Difference (B - A) |
|---|---:|---:|---:|
| **mAP50-95** | 0.8050 | 0.7506 | -0.0544 |
| **mAP50** | 0.9629 | 0.9431 | -0.0198 |
| **Recall** | 0.9326 | 0.9154 | -0.0172 |
| **Precision** | 0.9650 | 0.9535 | -0.0115 |
| **Inference Latency** | 15.65 ms | 19.45 ms | +3.80 ms |
| **Model Size** | 21.47 MB | 18.29 MB | -3.19 MB |

## Analysis & Recommendation

The candidate selected for Sciobraille V2 Master is **yolov8s_master_v2 (YOLOv8s)**.
Validation mAP50-95 reached **0.8050**.