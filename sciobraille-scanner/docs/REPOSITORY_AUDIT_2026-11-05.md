# SCIOBRAILLE repository audit — 5 November 2026

Baseline: 23d5faf577a4baddb722f64efa93469ae924519d. All modifications are isolated on codex/multilingual-accessible-scanner.

The repository contains the integrated native Kotlin Android/FastAPI product in sciobraille-scanner, training/data/benchmark provenance in sciobraille-model-lab, and upstream experiments in asmitha, prabh-decoders-braillevision, sangam-Braillie and braille_hackathon_siddhant. Older web/Flutter/Gradio apps are not the active product. No migration is needed.

The active YOLOv8s V2 checkpoint and INT8 Android asset exist in Git LFS. Both classify 26 English letters a–z. Earlier reports that V2 is missing are stale. Historical internal detection mAP is not independently measured physical-page text accuracy.

The backend already implements threaded, locked YOLO inference, bilateral preprocessing, optional mirror selection, duplicate suppression, row/spacing reconstruction, per-session stability, HTTP image upload and WebSocket scanning. The Android app uses CameraX, LiteRT, OkHttp, ML Kit translation/OCR, platform TTS, SharedPreferences history and Room learning progress. SQLite backs prototype school APIs. There are 57 English lessons across six levels plus Braille Studio and tactile/haptic tools.

## Findings before changes

| Severity | Finding | Impact |
|---|---|---|
| High | Camera scan takes one JPEG and forcibly marks it stable | No continuous scan; misleading stability |
| High | Existing TFLite detector disconnected from UI | Offline Braille scan unavailable |
| High | LMS API authentication accepts every request | School data must not be publicly exposed |
| High | Forced mirror ignores orientation preference | Natural raised-side Braille can fail |
| High | Translation callbacks not tied to current source/language | Stale result can overwrite current translation |
| Medium | Eleven translation targets; unofficial provider only | Limited coverage and reliability |
| Medium | Empty frames retain previous stability | Old page can remain visible as stable |
| Medium | Settings opens profile; history filters inert | Unimplemented controls appear functional |
| Medium | Gallery copy on UI thread; unbounded image decode | ANR/memory risk |
| Medium | Offline result capped at 80 boxes | Longer pages truncated |
| Medium | Response parser accepts empty JSON | Invalid backend response appears successful |
| Medium | Lessons locked behind unimplemented purchasing | Existing learning content inaccessible |
| Medium | No home/onboarding/dark theme/zoom/speech pause | Incomplete accessible product workflow |

Preserve real models and inference, historical data, all six LMS levels and progress, Studio/haptics/OCR, sharing/export utilities and test coverage. Never translate dictionary guesses as if recognized text. Grade-2 lesson content and Grade-1 text encoding do not demonstrate camera recognition of those standards.

Production evidence still requires representative physical images, measured CER/WER and Android device latency, TalkBack/device tests, a real HTTPS backend, and signing. General perspective correction, non-English Braille recognition, digits/punctuation/capital signs and contracted Braille are not validated by the current model.

## Training data and model provenance

The checked-in `sciobraille-model-lab/datasets/master_v2/dataset_statistics.json` records 5,001 candidates: Asmitha 1,325, Prabh 1,614 and Sangam 2,062. Deduplication removed 832 exact duplicates and 2,385 near/capture duplicates, retaining 1,784 images with 99,352 boxes. The recorded split is 1,440 training, 165 validation and 179 internal test images. Siddhant's 14 images had no labels and were excluded. Classes are strongly imbalanced: `o` has 9,658 boxes and `x` has 546. These are repository provenance records, not a new independent dataset audit or retraining run.

`models/v2_master/evaluation.json` records 30 epochs of YOLOv8s training at 640 pixels with AdamW and seed 20260923. Its historical internal test precision/recall are 0.9685/0.9339, mAP50 0.95348 and mAP50–95 0.79236. Those numbers are detector metrics on an internal split, not sentence accuracy. The September 25 promotion metadata and actual deployed checkpoint SHA-256 identify V2 as active; older notes saying V2 was missing are superseded. Original checkpoints and rollback metadata are retained.

The existing `reports/v2_int8_end_to_end_parity.md` is an explicit release concern: only 28/40 (70%) raw outputs exactly matched PyTorch, below its 90% target. Mean CER against PyTorch was 0.0198, but WER 0.0672 exceeded the 0.05 target. This compares engines with each other, not either engine against ground truth. The bundled artifact has float32 input/output despite its INT8 filename. Reconnecting it makes offline inference usable; it does not establish production parity. Device and server preprocessing also differ, so actual Android parity still needs measurement.

## Implementation and current evidence

The branch connects real continuous CameraX analysis and the bundled detector, retains the FastAPI inference service, adds multilingual provider adapters and installed-model translation, and repairs source/result state and learning access. [ARCHITECTURE.md](ARCHITECTURE.md) describes the modules and [VERIFICATION.md](VERIFICATION.md) records executed tests, physical-image error rates, failed live provider smoke tests and remaining release gates. No replacement model, retraining, full perspective correction or universal Braille support is claimed.
