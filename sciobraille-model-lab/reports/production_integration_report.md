# Sciobraille Production Integration Report

Date: 2026-09-19

## Result

Local integration completed without deploying or publishing anything.

The selected V1 Optimized checkpoint is byte-for-byte identical to the current backend production checkpoint. Therefore, the backend model file did not need to be replaced. The integration changed the inference contract and Android fallback behavior while preserving the model and its rollback file.

V2 Master was not integrated because `models/v2_master/best.pt` does not exist.

## Model Identity and Rollback

| Artifact | Size | SHA256 |
|---|---:|---|
| Previous production `sciobraille-scanner/backend/model/best.pt` | 22,537,258 bytes | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |
| Selected V1 `sciobraille-model-lab/models/v1_optimized/best.pt` | 22,537,258 bytes | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |
| Rollback `sciobraille-scanner/backend/model/best_previous_B.pt` | 22,537,258 bytes | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` |

Rollback metadata is stored in `sciobraille-scanner/backend/model/rollback/pre_integration_20260917.json`.

Because all three PT files have the same SHA256, this integration did not overwrite `backend/model/best.pt`.

## Frozen Benchmark

All recognition accuracy below uses `raw_text`. Spell correction and `corrected_text` never affect accuracy.

The frozen benchmark contains three physical phone-camera samples. This is useful for regression detection but is too small for a release-quality accuracy claim.

### Previous and Integrated PT

| Metric | Previous baseline | Final integrated PT |
|---|---:|---:|
| CER | 0.4010 | 0.3520 |
| WER | 0.6548 | 0.4643 |
| Character accuracy | 0.5990 | 0.6480 |
| Word accuracy | 0.3452 | 0.5357 |
| Exact sentence accuracy | 0.0000 | 0.0000 |
| Average latency | 304.34 ms | 270.94 ms |
| Median latency | 321.72 ms | 188.64 ms |

Model weights are unchanged. Improved raw accuracy comes from the selected V1 inference configuration: tuned confidence and IoU, bilateral preprocessing, TTA, class-agnostic duplicate removal, and adaptive reconstruction.

Detection metrics from the original YOLO validation split remain:

- Precision: 0.9572
- Recall: 0.9086
- mAP50: 0.9452
- mAP50-95: 0.7506

These detection metrics use the model's validation dataset, not the independent physical benchmark.

## Export Validation

Every export was tested against the same frozen physical benchmark.

| Format | Size | SHA256 | CER | WER | Median latency | Decision |
|---|---:|---|---:|---:|---:|---|
| PT | 22,537,258 | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` | 0.3520 | 0.4643 | 188.64 ms | Backend active |
| Fresh ONNX | 44,784,832 | `af2ae280055d9f9573d569a803a71ab99148cace5e56227f51c106d43ecfe368` | 0.4395 | 0.9881 | 425.59 ms | Rejected |
| Fresh float32 TFLite | 44,800,037 | `169e9914fe5f2483918a5eb3f3c2ce23b479f4da674ab74ea4286eec1d593093` | 0.4395 | 0.9881 | 2,220.63 ms | Rejected |
| Fresh INT8 TFLite | 11,551,143 | `e29e7c4c4e7977b7b034f6fbd20e380c3eda03b8467f42cdf9e90d1a44182de2` | 0.4849 | 1.2738 | 1,213.31 ms | Rejected |
| Existing validated float32 TFLite | 103,691,374 | `88440e300ef393652075bd18ca471dda43851247ba6f10deb4d9bc39bf4f0e18` | 0.3520 | 0.4643 | 4,075.72 ms | Retained reference |
| Existing Android INT8 TFLite | 26,381,430 | `9f6c45865ed2421041e8e46c865604ef953987382336c92bca91092d8eb5f4ad` | 0.3520 | 0.4643 | 2,387.80 ms | Android fallback active |

Fresh conversion artifacts remain under `sciobraille-model-lab/exports/v1_optimized/`. They were not copied into production because raw CER/WER regressed.

Fresh INT8 calibration used only 24 images. Ultralytics recommends more than 300 representative images. The fresh INT8 file is not acceptable for production.

Benchmark JSON files are under `sciobraille-model-lab/reports/exports/`.

## Backend Integration

Updated `sciobraille-scanner/backend/scanner_api.py`:

- Explicit confidence threshold: `0.50`
- Explicit model NMS IoU threshold: `0.50`
- Explicit post-detection duplicate IoU threshold: `0.70`
- Bilateral preprocessing and test-time augmentation enabled
- Canonical class order verified: `0=a` through `25=z`
- Horizontal flip remains enabled by default and can be overridden per request
- Adaptive line ordering and word spacing retained
- Duplicate suppression uses class-aware YOLO NMS followed by class-agnostic overlap removal
- REST stabilization is isolated by `client_id`
- WebSocket stabilization is isolated per connection
- Large page changes clear stale stabilization history
- Responses expose both `raw_text` and `corrected_text`
- Accuracy-sensitive raw output remains independent of correction

Live contract check:

- `GET /api/health`: HTTP 200
- `POST /api/scan-frame`: HTTP 200
- Reported classes: 26
- Reported confidence: 0.50
- Reported IoU: 0.50
- Response includes `raw_text`, `corrected_text`, boxes, confidence, and stability

Known physical sample raw output:

```text
jaihind
india
sciobraille
isually impaired
great project
```

Corrected output:

```text
jaihind
india
sciobraille
visually impaired
great project
```

## Android Offline Integration

Updated `sciobraille-scanner/android/app/src/main/java/com/sciobraille/scanner/MainActivity.kt`:

- Parses and preserves online `raw_text` and `corrected_text`
- Uses 640 by 640 offline model input
- Uses confidence 0.35 and class-agnostic duplicate IoU 0.70; this performed better for the retained TFLite export
- Uses canonical A-Z class ordering
- Mirrors camera input horizontally before offline inference to match backend default
- Uses class-agnostic duplicate suppression
- Uses adaptive line grouping and word spacing
- Uses per-scanner stabilization with stale-page reset
- Keeps offline corrected text equal to raw text because no offline spell checker exists

The existing validated Android asset remained active because the new INT8 export failed the accuracy gate:

`sciobraille-scanner/android/app/src/main/assets/best_int8.tflite`

## Tests and Build

Backend:

- Command: `python -m pytest tests -q`
- Result: 28 passed, 0 failed
- Remaining warning: external Starlette TestClient/httpx deprecation warning

Android:

- JDK: Android Studio bundled JBR 21.0.9
- Command: `gradlew.bat testDebugUnitTest assembleDebug --no-daemon`
- Result: build successful
- Unit tests: 14 passed, 0 failed
- Debug APK: `sciobraille-scanner/android/app/build/outputs/apk/debug/app-debug.apk`
- APK size: 59,631,451 bytes
- APK SHA256: `f93ea343bb045f5419ebb7f2a0cdbaa946782cf7217f187cde2cba739f0ce5d6`

No deployment, Play Store upload, or publication occurred.

## Regression Coverage Added

- Horizontal flip enabled and disabled
- Canonical class ordering
- Confidence, IoU, and image-size contract
- Adaptive word spacing
- Stabilization isolation between clients
- Stabilization reset after major text change
- Raw and corrected response parsing
- Android online response compatibility

## Remaining Limitations

1. V2 Master checkpoint is missing, so only V1 could be integrated.
2. Three benchmark images are insufficient for production accuracy claims. Add at least 50-100 independent physical samples across lighting, distance, blur, perspective, multiline text, and reverse-side Braille.
3. Fresh ONNX and TFLite exports materially reduced raw recognition accuracy and are not production-ready.
4. Existing accepted TFLite artifacts do not embed a cryptographic link to the source PT checkpoint. Their provenance depends on existing export metadata and benchmark evidence.
5. Online and offline preprocessing are behaviorally aligned but not pixel-identical. Backend can enhance images and retry raw input; Android performs RGB resize only.
6. Online spell correction is unavailable offline. Offline `corrected_text` therefore equals `raw_text`.
7. Reported TFLite latency was measured on Windows CPU, not the target Android phone.
8. Reverse-side flip mode still depends on correct input orientation or caller override.
9. Exact sentence accuracy remains zero on the small frozen benchmark.

## Release Decision

Local integration passes tests and Android debug build. Keep PT as backend runtime and existing validated INT8 TFLite as Android fallback. Do not promote fresh ONNX or TFLite exports. Do not claim release readiness until the physical benchmark is expanded and device-level latency and accuracy are measured.
