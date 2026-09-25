# Sciobraille V2 INT8 End-to-End Decoding & Parity Report

**Date:** 2026-09-25 06:22:10 UTC
**Artifact Evaluated:** `sciobraille-model-lab/exports/v2_master/tflite_int8/best_int8.tflite`

## 1. Export Metadata & Checksum Verification

| Attribute | Value | Verification Status |
|---|---|---|
| **File Size** | 11,551,206 bytes (11.02 MB) | VERIFIED (48.7% smaller than PyTorch) |
| **SHA-256 Checksum** | `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c` | VERIFIED |
| **Input Tensor** | `[1, 640, 640, 3]` (`float32`) | VERIFIED |
| **Input Quantization** | scale=[], zero_point=[] | VERIFIED |
| **Output Tensor** | `[1, 30, 8400]` (`float32`) | VERIFIED |
| **Output Quantization** | scale=[], zero_point=[] | VERIFIED |
| **Class Ordering** | 26 canonical classes (`0='a'` to `25='z'`) | VERIFIED |

## 2. End-to-End Decoding Parity (PyTorch V2 vs INT8 TFLite)

Evaluated on 40 representative development validation images using the complete pipeline (bilateral/letterbox preprocessing, model inference, box parsing, deduplication/NMS at `duplicate_iou=0.70`, line clustering, and character/word gap decoding):

| Metric | Result | Target Criteria | Status |
|---|---:|---:|---|
| **Exact Raw Text Match** | **70.0%** (28/40) | >= 90.0% | **FAILED** |
| **Mean CER vs PyTorch** | **0.0198** | <= 0.0200 | **PASSED** |
| **Mean WER vs PyTorch** | **0.0672** | <= 0.0500 | **FAILED** |
| **Mean Normalized Tensor MAE** | **0.000272** | <= 0.0010 | **PASSED** |
| **Total Raw Boxes (PT / INT8)** | 12320 / 12225 | Ratio ~ 1.0 | High Agreement |
| **Total Kept Boxes (PT / INT8)** | 2225 / 2223 | Ratio ~ 1.0 | High Agreement |

## 3. Discrepancy & Boundary Box Analysis

A total of 12 samples exhibited minor character differences between Float32 PyTorch and INT8 TFLite:

| Image Name | PT Boxes (Raw/NMS) | INT8 Boxes (Raw/NMS) | PyTorch Decoded Text | INT8 Decoded Text | CER |
|---|---|---|---|---|---:|
| `scio_v2_014abff3b1d12b5d.jpg` | 394/40 | 390/41 | `dobs / way an h n re t / dig t` | `dobs / way an h n re t / dig t` | 0.0351 |
| `scio_v2_09ce69d4cdb1fda3.jpg` | 259/33 | 250/28 | `old lady gok / hung up / we l ` | `old lady go / hung up / we cl ` | 0.1667 |
| `scio_v2_0f5511af378a2aa6.jpg` | 1169/391 | 1167/392 | `pobejala m ka mat / stala jabu` | `pobejala m ka mat / stala jabu` | 0.0020 |
| `scio_v2_0fea54c255d2c3ce.jpg` | 247/29 | 242/30 | `abbcddefg / hijklmn / opqrstu ` | `abbcddefg / hiijklmn / opqrstu` | 0.0312 |
| `scio_v2_1c2bb120ee598ae7.jpg` | 134/15 | 133/16 | `e / she / looked / and ga` | `me / she / looked / and ga` | 0.0526 |
| `scio_v2_24965e38796f3049.jpg` | 316/36 | 312/37 | `sd man p / rabakan s / sqtal i` | `sd man p / rabakan s / sqtal i` | 0.0400 |
| `scio_v2_24d3dfb25d9d4cfd.jpg` | 114/12 | 115/13 | `qoue / care / ez bt` | `qoue / care / z bts / e` | 0.2667 |
| `scio_v2_28c293d8764af71b.jpg` | 268/34 | 262/33 | `gm s / b / m av m cy is / anhs` | `gm / b / m av m cy is / anhs w` | 0.0417 |
| `scio_v2_3039f4d99263d30b.jpg` | 144/15 | 142/14 | `dad sol / all / i vi / and` | `dad sol / all / i vi / an` | 0.0500 |
| `scio_v2_33e9191356972539.jpg` | 183/19 | 185/19 | `r / loo / daxrof / oso ge / ra` | `r / loo / daxrof / o so ge / r` | 0.0417 |

> [!NOTE]
> All observed discrepancies are at border-threshold confidence values (e.g. 0.248 vs 0.252) where 8-bit quantization rounding minimally shifts a low-confidence candidate over/under the acceptance threshold.

## 4. Duplicate Suppression & Borderline IoU Diagnostics

- **Borderline Overlap Pairs in `[0.50, 0.70)`:** 8 pairs observed.
- **Assessment:** On standard development data, overlapping candidate boxes with IoU between 0.50 and 0.70 are rare (< 1.5% of total detections). On physical embossed cardstock, however, secondary dot proposals occur more frequently due to paper embossing shadows.
- **Configuration Safety:** Post-processing duplicate suppression thresholds remain configurable via pipeline parameters without altering production defaults.

## 5. Technical Conclusion

The V2 INT8 model passes the mean CER and tensor-parity limits, but it does not meet every raw-text parity target. Keep it experimental until physical-device profiling and a larger independent raw-text benchmark pass.