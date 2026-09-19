# Sciobraille Final Project Audit

Date: 2026-09-19

## Scope and Method

This audit covered the native Android application, CameraX scanner, FastAPI scanner and LMS APIs, PT and TFLite inference, reconstruction, stabilization, history, Room LMS storage, SQLite backend storage, builds, tests, and the frozen physical-image benchmark.

The workspace contains no Git metadata at its root or in `sciobraille-scanner` and `sciobraille-model-lab`. Therefore, historical modified-file status cannot be reconstructed with `git status`. This pass changed only the files listed under "Fixes Applied." No model, dataset, archive, or database file was deleted.

## CRITICAL

### Resolved

1. **Backend inference configuration had drifted from the selected V1 winner.** It used confidence 0.35, IoU 0.70, and no TTA. The measured winner uses confidence 0.50, IoU 0.50, bilateral preprocessing, TTA, class-agnostic duplicate IoU 0.70, and median-based adaptive reconstruction. The backend now matches that configuration.
2. **Release signing values existed in `android/local.properties` without an ignore rule.** The values were not printed, copied, or committed. A project `.gitignore` now excludes `local.properties`, keystores, runtime databases, caches, and build output. Rotate those signing credentials if this directory was ever shared or committed elsewhere.

## HIGH

### Resolved

1. **Backend and Android LMS curricula disagreed.** Backend had 50 generic lessons while Android seeds 57 lessons with exact IDs. Backend now exposes matching IDs and level counts: 1, 26, 6, 10, 11, and 3.
2. **REST inference blocked the FastAPI event loop.** `POST /api/scan-frame` now runs inference in a worker thread.
3. **WebSocket flip override was ignored.** `/ws/scan?flip_horizontal=false` now reaches inference and was verified over a real socket.
4. **A stalled WebSocket could stop Android scanning after two pending frames.** Android now cancels the stale socket after five seconds and switches to device fallback.
5. **Malformed WebSocket JSON could escape the callback.** Parsing now fails safely and activates fallback.
6. **Offline stabilization could preserve text across scan sessions.** Start and Stop reset the offline history.
7. **Different-class overlapping boxes could survive backend post-processing or be suppressed incorrectly offline.** Both paths now use class-agnostic post-detection duplicate removal at IoU 0.70.
8. **Older Android versions could crash on `removeLast()`.** The code now uses `removeAt(lastIndex)`.
9. **TensorFlow Lite native libraries triggered a 16 KB page-size warning.** Android now uses LiteRT 1.4.1. Final lint contains no 16 KB alignment finding.

### Open

1. **V2 Master model checkpoint does not exist.** Master V2 dataset is complete, but `models/v2_master/best.pt` is absent. No V2 model can be integrated or compared.
2. **LMS authentication is a placeholder.** `require_lms_auth` currently accepts every request. The backend is suitable only for trusted local prototype use and must not be publicly exposed.

## MEDIUM

### Resolved

1. Empty, corrupt, wrong-MIME, oversized-byte, and excessive-dimension images now return predictable API errors.
2. POST requests without a client ID are stateless. Named sessions and WebSocket histories are isolated.
3. Camera startup, missing flash, unavailable TTS, malformed history, sharing failures, and scanner-empty states have guarded behavior.
4. Debug and release backend URLs are separated. Debug points to the current LAN server; release remains HTTPS-only.
5. Runtime `*.db`, `*.sqlite`, and `*.sqlite3` files are ignored without deleting the existing database.
6. Standalone `inference.py` now uses V1 confidence 0.50 and model IoU 0.50.

### Open

1. Frozen physical benchmark has only three samples. It cannot support a production accuracy claim or category-level lighting and distance statistics.
2. Release backend URL is still `https://replace-with-your-sciobraille-backend.example.com`; release networking will not work until a real HTTPS endpoint is configured.
3. Camera preview, permissions, torch, TalkBack, TTS, haptics, Room persistence after process death, and phone TFLite latency were not exercised on a physical device in this pass.
4. Fresh ONNX and TFLite exports regress raw recognition. Android retains the previously validated TFLite artifact instead.
5. Existing Android TFLite provenance is benchmark-based; it lacks a cryptographic source-link to the PT checkpoint.
6. Python environment has one dependency conflict: `roboflow 1.3.9` requires `typer<0.26`, while `typer 0.26.6` is installed. Scanner tests still pass.
7. Automatic front-side versus reverse-side orientation selection is not implemented. Caller-selected horizontal flip remains necessary for some images.

## LOW

1. Android lint reports 199 warnings and zero errors: 181 `SetTextI18n`, 7 `UseKtx`, 6 `DrawAllocation`, and five single warnings. No accessibility or 16 KB alignment errors remain.
2. Camera permission handling uses deprecated `onRequestPermissionsResult`; migration to Activity Result API is recommended later.
3. Gradle reports deprecated features that will need attention before Gradle 10.
4. Voice-answer speech recognition, Word Reading Challenge mode, PDF certificate download, payments, and verified school-code activation remain explicit placeholders.

## Fixes Applied

- `sciobraille-scanner/backend/scanner_api.py`
- `sciobraille-scanner/backend/inference.py`
- `sciobraille-scanner/backend/lms_api.py`
- `sciobraille-scanner/backend/tests/test_scanner_api.py`
- `sciobraille-scanner/backend/tests/test_scanner_preprocessing.py`
- `sciobraille-scanner/backend/tests/test_lms_api.py`
- `sciobraille-scanner/android/app/build.gradle`
- `sciobraille-scanner/android/app/src/main/java/com/sciobraille/scanner/MainActivity.kt`
- `sciobraille-scanner/android/app/src/test/java/com/sciobraille/scanner/ResponseParserTest.kt`
- `sciobraille-scanner/.gitignore`
- Documentation and final benchmark/report files under `sciobraille-scanner` and `sciobraille-model-lab/reports`.

## Verification Summary

- Backend: 28 tests passed; one external TestClient deprecation warning.
- Real HTTP and WebSocket: health and scan succeeded; raw/corrected separation and flip override verified.
- Android: 14 unit tests passed; debug APK and release AAB built.
- Android lint: zero errors, zero accessibility findings, zero 16 KB findings.
- SQLite: integrity check `ok`; all expected tables exist.
- PT and Android TFLite: both load and produce matching raw results on all three frozen samples.
- Python files compile. Global `pip check` reports the Roboflow/Typer conflict above.
