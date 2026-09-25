# Sciobraille Final Model and App Selection

**Date:** 2026-09-25
**Branch:** `feat/v2-master-model`

## Decision

The final phone APK retains V1 as its active production model. V2 Master remains a validated experimental model and is available through the separate `v2Test` Android variant and backend launcher.

This decision is evidence-based:

- V2 improves detection metrics on the frozen Master V2 internal test split.
- V1 produces better raw recognition text on the small physical regression set.
- The physical set has only three captures from two documents, so it is not sufficient to certify either model for broad real-world use.

No DMI image was used for training, epoch selection, augmentation tuning, or V2 candidate selection. V2 selection used the Master V2 validation split. DMI images were read only after training as regression inputs.

## Model Results

| Metric | V1 production | V2 Master |
|---|---:|---:|
| Internal-test precision | 0.9375 | 0.9685 |
| Internal-test recall | 0.8591 | 0.9339 |
| Internal-test mAP50 | 0.9182 | 0.9535 |
| Internal-test mAP50-95 | 0.7302 | 0.7924 |
| Three-image physical raw CER | 0.3520 | 0.3963 |
| Three-image physical raw WER | 0.4643 | 0.5952 |

V2's physical regression is mainly caused by duplicate detections and embossed-paper shadow artifacts. It recovers some faint cells that V1 misses, but inserts more false cells on the current physical samples.

## DMI Input Results

The production backend pipeline was run directly against both supplied images with its normal preprocessing, confidence, IoU, duplicate suppression, and horizontal-mirror behavior.

### `DMI.jpeg`

| Model | Raw output | Detections |
|---|---|---:|
| V1 | empty | 0 |
| V2 | empty | 0 |

This capture shows the opposite/indented relief and neither trained detector recognizes it reliably. A geometric horizontal flip alone does not convert this relief into the raised-side appearance used by the training data.

### `Flipped DMI.jpeg`

| Model | Raw output | Corrected display output |
|---|---|---|
| V1 | `dmi college\nof engineerin` | `dmi college\nof engineering` |
| V2 | `dmi collige\nof engineerin` | `dmi college\nof engineering` |

V1 is better on raw text for this image. Accuracy comparisons use only `raw_text`; corrected display text is listed separately.

## Selected Artifacts

- Production backend PT: `sciobraille-scanner/backend/model/best.pt`
- Production PT SHA-256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- Production Android INT8: `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite`
- Production Android INT8 SHA-256: `9f6c45865ed2421041e8e46c865604ef953987382336c92bca91092d8eb5f4ad`
- Experimental V2 PT: `sciobraille-model-lab/models/v2_master/best.pt`
- Experimental V2 PT SHA-256: `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62`
- Experimental V2 INT8 SHA-256: `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c`

V2 INT8 parity over 40 validation images: mean CER `0.0198` and normalized tensor MAE `0.000272` pass configured limits, while exact raw-text match `70.0%` and mean WER `0.0672` do not. This is another reason V2 remains experimental.

## Final APK

- File: `sciobraille-scanner/releases/Sciobraille-Final-V1-2026-09-25.apk`
- Size: 51,360,465 bytes
- SHA-256: `40c7388c51fddfc5c0e7ac345bd471e907b5d27d3c05fcceff392189d9349774`
- Package: `com.sciobraille.scanner`
- Signature: Android debug certificate, APK Signature Scheme v2 verified
- Bundled active model: V1 INT8 only

This APK is suitable for direct local installation and device testing. It is not a Play Store release because it uses a debug signing certificate.

## Verification

- Backend tests: 28 passed.
- Android debug unit tests: 14 passed.
- Android V2 test unit tests: 14 passed.
- Android `assembleDebug`: passed.
- Android `assembleV2Test`: passed.
- APK signature verification: passed.
- Physical Android device execution: not performed because no ADB device was connected.

## Remaining Work

1. Collect 50-100 independent phone-camera Braille samples with exact raw ground truth.
2. Include raised-side and reverse/indented-side captures, lighting, blur, range, and perspective metadata.
3. Train reverse-side examples only after independent collection and annotation; do not derive training labels from these two DMI test images.
4. Re-evaluate V1 and V2 on the frozen independent set before promoting V2.
5. Configure a stable HTTPS backend and release signing before Play Store distribution.
