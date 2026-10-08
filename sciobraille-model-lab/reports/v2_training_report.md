# Sciobraille V2 Training Report

**Date:** 2026-09-24 16:16:16 UTC

## 1. Environment & Hardware

- **Platform:** `Windows-10-10.0.26200-SP0`
- **Python:** `3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]`
- **PyTorch:** `2.8.0+cu128`
- **Ultralytics:** `8.4.14`
- **CUDA Available:** `True`
- **CUDA Device:** `NVIDIA GeForce RTX 3050 6GB Laptop GPU` (6.0 GB VRAM)

## 2. Dataset Lineage & Splits

- **Dataset Path:** `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\sciobraille-model-lab\datasets\master_v2\data.yaml`
- **Dataset Fingerprint (SHA-256):** `9d115c9074676596aaaf7c01bcda68e81aba89b47ac237c9f8d4083495fbd699`
- **Retained Images:** `1784`
- **Total Bounding Boxes:** `99352` (Train: 82,291, Val: 7,773, Test: 9,288)
- **Train Images:** 1440
- **Validation Images:** 165
- **Internal Test Images:** 179
- **Canonical Classes:** 26 (`0=a` through `25=z`)

## 3. Augmentation Strategy (Embossed-Braille Safe)

- **Geometric:** `flipud=0.0`, `fliplr=0.0` (preserves dot semantics), `degrees=3.0`, `scale=0.12`, `mosaic=0.10`
- **Photometric:** Brightness +/-10%, Contrast +/-12%, Gamma [0.92, 1.08], Blur p=0.08, Noise p=0.10, Shadow p=0.10

## 4. Trained Candidates Summary

| Candidate | Architecture | Epochs | Best Val mAP50-95 | Best Val mAP50 | Best Val Recall | Precision | Latency (ms) | Checkpoint SHA-256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `yolov8s_master_v2` | YOLOv8s | 30 | **0.8050** | 0.9629 | 0.9326 | 0.9650 | 15.65 ms | `8e32d074e0ed` |
| `yolo11s_master_v2` | YOLO11s | 30 | **0.7506** | 0.9431 | 0.9154 | 0.9535 | 19.45 ms | `30b81c5a8d70` |

## 5. Checkpoint Selection

- **Selected Architecture:** `YOLOv8s` (`yolov8s_master_v2`)
- **Selected Checkpoint:** `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\sciobraille-model-lab\models\v2_master\experiments\yolov8s\weights\best.pt`
- **Selected Checkpoint SHA-256:** `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62`
- **Selection Criteria:** Maximizing validation `mAP50-95` on Master V2 validation split.
- **Destination:** `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\sciobraille-model-lab\models\v2_master\best.pt`