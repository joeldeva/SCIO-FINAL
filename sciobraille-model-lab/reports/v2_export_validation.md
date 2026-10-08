# Sciobraille V2 Model Export & Validation Report

**Date:** 2026-09-24 17:54:53 UTC

## 1. Exported Artifacts Summary

| Format | File Path | File Size | SHA-256 | Target Runtime | Status |
|---|---|---:|---|---|---|
| **PyTorch (Baseline)** | `models/v2_master/best.pt` | 21.47 MB | `8e32d074e0edb12c...` | Python Backend | VERIFIED |
| **ONNX** | `exports/v2_master/onnx/best.onnx` | 42.79 MB | `ae25ae51f4557470...` | High-throughput server | PASSED |
| **Float32 TFLite** | `exports/v2_master/tflite_float/best_float32.tflite` | 42.72 MB | `cc08d63240b6b7ee...` | Desktop / Mobile FP32 | PASSED |
| **INT8 TFLite** | `exports/v2_master/tflite_int8/best_int8.tflite` | 11.02 MB | `7e5cf70ecb47f868...` | Mobile LiteRT / Edge TPU | PASSED |

## 2. Tensor Specifications & Quantization Parameters

### PyTorch / ONNX
- Input Shape: `[1, 3, 640, 640]` (Float32 normalized [0.0, 1.0])
- Output Shape: `[1, 30, 8400]` (4 box coordinates + 26 class scores across 8,400 anchors)
- Classes: 26 canonical classes (`0=a` through `25=z`)

### INT8 Quantized TFLite
- Calibration Dataset: 1,440 images from Master V2 training split (`images/train`).
- Input Tensor: Shape `[1, 640, 640, 3]`, Type `float32`
- Input Quantization: Scale = `0.0`, Zero-Point = `0`
- Output Tensor: Shape `[1, 30, 8400]`, Type `float32`
- Output Quantization: Scale = `0.0`, Zero-Point = `0`
- Size Reduction: **21.47 MB -> 11.02 MB (48.7% reduction)**

## 3. Output Parity Against PyTorch Baseline

Evaluated on 20 development validation images from Master V2:

| Comparison Pair | Mean Absolute Error (MAE) | Max Absolute Diff | Parity Assessment |
|---|---:|---:|---|
| **PyTorch vs ONNX** | `0.000015` | `0.000080` | **Exact Numerical Parity** (< 1e-4) |
| **PyTorch vs Float32 TFLite** | `0.000000` | - | **Near-Exact Parity** |
| **PyTorch vs INT8 TFLite** | `0.000258` | - | **Expected Quantization Noise** |

## 4. Inference Latency Benchmarks (Desktop Runtime)

| Model Format | Average Latency (ms) | Median Latency (ms) | Std Dev (ms) |
|---|---:|---:|---:|
| **PyTorch (GPU)** | 173.47 ms | 170.37 ms | 9.48 ms |
| **ONNX (CPU)** | 121.5 ms | 114.22 ms | 20.58 ms |
| **Float32 TFLite (CPU)** | 678.63 ms | 678.85 ms | 32.56 ms |
| **INT8 TFLite (CPU)** | 319.84 ms | 319.85 ms | 28.15 ms |

> [!NOTE]
> Desktop CPU TFLite interpreter latency does not reflect mobile hardware acceleration (NPU/Hexagon DSP/GPU via LiteRT). Physical Android device profiling must be performed.

## 5. Safety Compliance
- `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite` was **NOT** modified or overwritten.
- Production weights `sciobraille-scanner/backend/model/best.pt` remain unchanged.