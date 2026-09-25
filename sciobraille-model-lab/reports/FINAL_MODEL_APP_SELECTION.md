# Sciobraille Final Model and App Selection

**Date:** 2026-09-25
**Branch:** `feat/v2-master-model`

## Decision

Sciobraille V2 Master YOLOv8s is now the active backend and Android offline model. The user selected V2 after a controlled comparison on two new SSN captures. Those captures were used only for inference testing and were not added to training data.

V1 remains available for rollback. No historical model or source dataset was deleted.

## Active Artifacts

| Target | Path | SHA-256 |
|---|---|---|
| Backend PyTorch | `sciobraille-scanner/backend/model/best.pt` | `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62` |
| Android INT8 | `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite` | `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c` |
| Final APK | `sciobraille-scanner/releases/Sciobraille-Final-V2-2026-09-25.apk` | `6374c98fa90da7b6799ee321097ba464b360e4bf6c99c1a0840d725c3faa2082` |

## Rollback

| Artifact | Path | SHA-256 |
|---|---|---|
| V1 PyTorch | `sciobraille-scanner/backend/model/best_previous_B.pt` | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |
| V1 lab model | `sciobraille-model-lab/models/v1_optimized/best.pt` | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |
| V1 Android INT8 | `sciobraille-scanner/backend/model/best_saved_model/best_int8.tflite` | `9f6c45865ed2421041e8e46c865604ef953987382336c92bca91092d8eb5f4ad` |

Full promotion metadata is stored in `sciobraille-scanner/backend/model/rollback/v2_promotion_20260925.json`.

## V2 Metrics

| Metric | Result |
|---|---:|
| Internal-test precision | 0.9685 |
| Internal-test recall | 0.9339 |
| Internal-test mAP50 | 0.9535 |
| Internal-test mAP50-95 | 0.7924 |
| Average PyTorch latency | 15.65 ms |
| Median PyTorch latency | 15.83 ms |

The independent physical benchmark is still too small for broad production claims. Accuracy measurements use raw recognition output only.

## Runtime Changes

- Confidence threshold: `0.25`
- IoU threshold: `0.45`
- Duplicate IoU threshold: `0.70`
- Test-time augmentation: disabled
- Both front and horizontally mirrored orientations are evaluated automatically.
- Text is decoded in model coordinates before overlay coordinates are mapped back to the camera preview.
- Generic English bigram scoring selects orientation. It does not replace detected characters.
- Primary `text` uses stabilized `raw_text`. Optional spell output remains isolated in `corrected_text`.

## SSN Regression

| Input | Selected orientation | Raw output |
|---|---|---|
| `SSN INVENTE.png` | original | `ss invente` |
| `SSN INVENTE 2.jpeg` | horizontally flipped | `ss invente` |

## Verification

- Backend tests: 30 passed.
- Android debug unit tests: 15 passed.
- Android debug APK build: passed.
- Active backend and Android model hashes match V2 source artifacts.
- Final releases directory contains one APK only.
- Physical Android device execution was not performed because no ADB device was connected.

## Deployment Artifact

- File: `sciobraille-scanner/releases/Sciobraille-Final-V2-2026-09-25.apk`
- Size: 51,360,465 bytes
- Package: `com.sciobraille.scanner`
- Signing: Android debug certificate for direct device testing

This APK is not Play Store-ready. Play Store distribution still requires release signing, a production HTTPS backend, and real-device acceptance testing.
