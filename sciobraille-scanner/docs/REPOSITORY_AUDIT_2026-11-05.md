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
