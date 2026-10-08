# Sciobraille Final Model Comparison: V1 Production vs V2 Master

Head-to-head comparison between active production V1 model and newly trained V2 Master model under equivalent evaluation conditions on the Master V2 dataset.

## Model Identification

| Attribute | Production V1 | Master V2 Winner |
|---|---|---|
| **Architecture** | YOLOv8s | YOLOv8s |
| **Checkpoint Path** | `sciobraille-scanner/backend/model/best.pt` | `sciobraille-model-lab/models/v2_master/best.pt` |
| **SHA-256** | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` | `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62` |
| **Training Dataset** | Prabh merged (1,614 images) | Master V2 (1,784 unique images, 99,352 boxes) |
| **Model Size** | 21.49 MB | 21.47 MB |

## Evaluation Metrics on Master V2 Validation Split (165 images)

| Metric | Production V1 Baseline | Master V2 Winner | Delta (V2 - V1) |
|---|---:|---:|---:|
| **mAP50-95** | 0.7504 | 0.8050 | +0.0545 |
| **mAP50** | 0.9307 | 0.9629 | +0.0322 |
| **Recall** | 0.8745 | 0.9326 | +0.0581 |
| **Precision** | 0.9308 | 0.9650 | +0.0342 |
| **Inference Latency** | 15.92 ms | 15.65 ms | -0.27 ms |

## Internal Test Split Evaluation (179 images - Unbiased Post-Selection)

| Metric | Production V1 | Master V2 Winner | Delta (V2 - V1) |
|---|---:|---:|---:|
| **Test mAP50-95** | 0.7302 | 0.7924 | +0.0621 |
| **Test mAP50** | 0.9182 | 0.9535 | +0.0353 |
| **Test Recall** | 0.8591 | 0.9339 | +0.0748 |
| **Test Precision** | 0.9375 | 0.9685 | +0.0310 |

## Physical Benchmark (3 Samples - Regression Check Only)

| Metric | Production V1 | Master V2 Winner |
|---|---:|---:|
| **Raw CER** | 0.3520 | 0.3963 |
| **Raw WER** | 0.4643 | 0.5952 |
| **Raw Character Accuracy** | 0.6480 | 0.6037 |
| **Raw Word Accuracy** | 0.5357 | 0.4048 |

> [!IMPORTANT]
> The 3-image physical benchmark is preserved for regression testing only and is insufficient for real-world certification. Real-world physical performance remains provisional pending collection of 50-100 independent field samples.