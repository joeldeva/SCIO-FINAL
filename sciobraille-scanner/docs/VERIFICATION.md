# Verification — 6 November 2026

This report separates executed checks from work requiring a device, provider account or additional data. This is a development build; production readiness is not claimed.

## Executed

- Final code build: [GitHub run 42161440217](https://github.com/joeldeva/SCIO-FINAL/actions/runs/42161440217), commit `a33eb672c16ef20e5bffd0669e032191da2c6968`. `testDebugUnitTest`, `lintDebug`, `assembleDebug` and `connectedDebugAndroidTest` succeeded. **49 JVM tests and 3 instrumented Android tests passed, zero failures/errors/skips.** JVM tests cover Activity/resources navigation, dark/extra-large text recreation (Robolectric API 34), state, languages, reading order, speech requests, history, network failures/recovery and LMS. Rendered light/dark/large-text screens were inspected; the navigation wrapping issue is corrected.
- Native Android tests ran on an **API 34 x86_64 emulator**. Real bundled TFLite inference on `test_sciobraille.jpeg` returned 50 cells; raw output and the 1,520 ms first invocation are in `android_inference_2026-11-06.json`. This is an emulator measurement, not a phone latency promise or an accuracy pass. The model was not mocked.
- An actual Tamil ML Kit model was downloaded, then `TranslationRepository` translated a fixed English sample with backend access disabled. **Local Tamil output was returned**, recorded in `android_tamil_translation_2026-11-06.json`. The sample output omits the word “Braille”; a successful response does not establish semantic accuracy. There was no human quality scoring or airplane-mode packet capture. Other languages and TTS engines remain separate validation work.
- The native certificate test generated a seven-page PDF containing Tamil, Hindi, Arabic and Chinese text and rendered every page using Android PdfRenderer. The first page was visually inspected with Unicode glyphs present and no overlap. These are test data, not an awarded certificate. PDF output is not tagged for accessibility; accessible plain text remains available in the app.
- APK signature verification succeeded. Downloaded APK size: **142,894,243 bytes** (about 136.3 MiB). SHA-256: `c31ae3cf5ea39bf8d6d6e9114348a3969c652832ecbc69b53313bf95d8b0e998`. The model asset inside the APK matches the source model hash below. This is a debug-signed development APK, not a production release.
- Android lint: **0 errors, 261 warnings**. Warnings include existing hardcoded UI strings, draw allocations and deprecated APIs. Passing lint does not mean all warnings or accessibility issues are resolved.
- Backend: **41 tests passed**, one Starlette/httpx deprecation warning; `docs/backend-junit.xml`. Tests cover endpoints, image limits, per-client/blank stability, Google/Libre/community adapter contracts, Unicode, unsupported inputs, provider errors/timeouts, prototype LMS isolation and geometry. Provider contract tests use explicit fixtures, not real translation responses.
- Real YOLO inference through HTTP and WebSocket routes: `docs/real_inference_smoke_2026-11-05.json`. HTTP returned 51 cells on the physical sample; WebSocket raw output agreed, and the second identical frame was marked stable. These calls use FastAPI's in-process transport; phone networking is not measured.
- Real bundled TFLite invocation on Linux: `docs/tflite_smoke_2026-11-05.json`. Asset size **11,551,206 bytes**, SHA-256 `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c`; input `[1,640,640,3]`, output `[1,30,8400]`, float32 I/O. Its filename is `best_int8.tflite`; do not infer integer input/output from the filename. One host invocation returned finite outputs and 463 candidate anchors above 0.25 before NMS. This validates an executable artifact, not Android parser parity or phone performance.
- An explicit legacy community-service smoke attempted 14 target languages. **All 14 failed** from this environment (timeouts/provider failures). See `docs/live_service_smoke_2026-11-05.json`. No successful live community-service translation or human quality rating is claimed. That failure motivated replacing the unbounded synchronous community call with bounded asynchronous HTTP. A further bounded-HTTP smoke on 6 November retried Tamil, Hindi and French after installing the workspace proxy dependency; all three returned HTTP 302 and were treated as failures. The Tamil redirect pointed to `www.google.com/sorry/index` and was not followed. Official Google/Libre adapters require a configured service/account for live verification. The successful installed-model Tamil test above is a separate path.

## Physical recognition regression

Script: `backend/scripts/evaluate_physical.py`. Results: `physical_regression_2026-11-05.json`. Actual deployed model SHA-256: `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62`.

Three repository photographs with existing ground truth were tested, plus 12 synthetic variants (50% light reduction, Gaussian blur, 8-degree rotation and perspective warp). Fixed orientation follows each existing benchmark row. Current and baseline `23d5faf577a4baddb722f64efa93469ae924519d` use the same weights. Raw text is measured; dictionary correction is not counted as recognition.

| Original photograph | Character error rate | Word error rate |
|---|---:|---:|
| `test_sciobraille.jpeg` | 5.26% | 28.57% |
| `DMI.jpeg` (benchmark mirror setting) | 100% | 100% |
| `Flipped DMI.jpeg` | 3.85% | 25% |
| Macro mean | **36.37%** | **51.19%** |

The current and baseline original-image error rates are identical. No accuracy gain is claimed. No new weights were trained or quantized. Mild row deskew is tested geometrically but this set does not establish an accuracy improvement. The DMI photographs are closely related views and the small set is not independent; it is not representative of worldwide Braille, arbitrary paper/camera types or production accuracy.

The recorded local run's median of three original-image per-case median predictions was about **192 ms** current and **429 ms** baseline on Linux CPU with two Torch threads. These timings fluctuate with shared host scheduling, warm-up and processing conditions. They exclude camera/JPEG, network, UI, translation and speech. Do not present the difference as an optimization gain or promise phone latency. Detailed per-case times, runtime versions, ground truth and raw output are preserved in JSON. CI also emits its own report.

## Not executed / release gates

- Physical Android camera preview/overlay, capture/gallery, flash/zoom, orientation and physical-phone end-to-end scan→translate→speech. Emulator inference is tested; physical-phone inference/latency still needs validation.
- ML Kit models beyond the tested Tamil download, installed speech voices, airplane-mode packet inspection, TTS pause/resume/locale quality and background/audio-focus behavior on real engines.
- Human TalkBack checks, low-vision usability, 200% system font, all device sizes and API 26–36 compatibility.
- Device end-to-end p50/p95 latency, peak memory, battery and thermal tests; no phone FPS/accuracy target is asserted.
- Representative independent physical-page evaluation and retraining. General perspective rectification, arbitrary rotations, digits, capitalization, punctuation and contracted/non-English Braille recognition remain unsupported.
- Official online translation with deployment credentials, all 133 catalog targets, language experts' translation assessment, secure public backend deployment, school-account authorization and production upload signing.

Follow [DEVICE_ACCEPTANCE.md](DEVICE_ACCEPTANCE.md). Select a representative test set and acceptance thresholds before making a production claim. Historical detector mAP and old README outputs are not replacements for this evidence.
