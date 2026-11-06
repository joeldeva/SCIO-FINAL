# SCIOBRAILLE

Native Android assistive Braille scanning, translation and speech, built on the existing Kotlin/CameraX, LiteRT and FastAPI/YOLO application. Development version **1.2.1-dev**. This branch is an integrated development build, **not a production certification**.

Development APKs now install as **SCIOBRAILLE Dev** (`com.sciobraille.scanner.dev`) alongside the original SCIOBRAILLE (`com.sciobraille.scanner`). The new app starts with separate history, preferences and learning progress; it does not replace or erase the original app's data. This fixes the package/signing conflict encountered with the 1.2.0 development APK. Release identity stays unchanged.

Verified development build: [run 42203795652](https://github.com/joeldeva/SCIO-FINAL/actions/runs/42203795652), source commit `2ea2e666d1e577b49003e58da43135903430bb0b`. **49 JVM, 3 Android emulator and 41 backend tests passed**; APK signature verified; lint reports 0 errors and 261 warnings. The workflow's Android artifact contains the APK and reports (retained for 30 days). [Checksums, actual model/translation results and limits](docs/VERIFICATION.md).

The camera model recognizes **English letters a–z**. Translating its English output into Tamil, Hindi or another language does not enable recognition of that language's Braille writing system. Capitals, numbers, punctuation signs, contracted Grade 2 and Bharati camera recognition are not validated or advertised as supported.

## Use the app

1. Open Home → Start live scan. Grant camera permission when requested; photo import also works without camera permission.
2. Hold a flat, well-lit Braille page steady. Use zoom/flash if available, pause/restart, or choose Photo to capture/import an image. For reverse-side embossing choose the orientation in Settings.
3. Review the recognized text. Low-confidence cells are flagged; use Review to correct text. A repeated reading is stable, not necessarily correct.
4. Choose a target language and Translate. Original and translated text stay separate. Copy, share, save or use speech controls.
5. View saved readings and translations in History. Search, filter by date, reuse or delete them. History is capped at 50 entries on this device.
6. Learn opens the existing six-level curriculum and locally stored progress. Settings controls themes, contrast, text size, speech, processing mode and the backend address.

The app includes a **133-entry translation catalog**, with searchable native names, favorites and recent selections. Actual online availability comes from the configured provider. Offline translation is limited to ML Kit supported models that the user downloads. TTS depends on the voices on the phone. See [the full language matrix](docs/LANGUAGES.md).

## Clone and build an APK

Use Git LFS, JDK 17, Android SDK platform 36 and build tools 35.0.0. Minimum supported Android version is 8.0 (API 26). The Gradle wrapper is 8.13, Android Gradle Plugin 8.13.2, Kotlin 2.0.21.

```sh
git clone --branch codex/multilingual-accessible-scanner https://github.com/joeldeva/SCIO-FINAL.git
cd SCIO-FINAL
git lfs pull --include='sciobraille-scanner/android/app/src/main/assets/best_int8.tflite,sciobraille-scanner/backend/model/best.pt,sciobraille-model-lab/benchmark/images/*,DMI.jpeg,Flipped DMI.jpeg'
cd sciobraille-scanner/android
# Configure SDK location in local.properties or ANDROID_HOME.
./gradlew :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

On Windows use `gradlew.bat`. Android Studio can open the `android` directory. Do not package the small Git LFS pointer instead of the actual model. Debug APKs use a development signing key; an installed APK signed with another key cannot be updated in place. Uninstalling erases local history and lesson progress.

The GitHub **SCIOBRAILLE build and verification** workflow produces a debug APK, test reports and rendered screen checks. Its debug APK has no public backend preconfigured. Offline recognition is bundled; set a backend in Settings for online requests.

For a store build, configure your existing upload keystore using `SCIOBRAILLE_UPLOAD_STORE_FILE`, `SCIOBRAILLE_UPLOAD_STORE_PASSWORD`, `SCIOBRAILLE_UPLOAD_KEY_ALIAS`, `SCIOBRAILLE_UPLOAD_KEY_PASSWORD` in private local properties or CI secrets, then `./gradlew :app:bundleRelease`. Release builds deliberately refuse to package without signing configured. Do not commit the keystore/passwords. [Release signing details](docs/RELEASE_SIGNING.md).

## Run the existing backend

Python 3.12 is used for verification. CPU installation avoids downloading CUDA dependencies when no GPU is available.

```sh
cd sciobraille-scanner/backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-runtime.txt
uvicorn scanner_api:app --host 127.0.0.1 --port 8088 --workers 1 --limit-concurrency 16 --ws-max-size 20971520
```

Use `requirements-runtime.txt` for the mobile API; the original `requirements.txt` remains for desktop/training demos. Open `/api/health` to verify real model initialization. Recognition endpoints remain `POST /api/scan-frame` (multipart `frame`) and `/ws/scan` (binary image frames). `/api/capabilities` reports the supported recognition system. `/api/languages` reports current translation targets. Requests to `/api/translate` use `text`, `source_lang` (`en` or `auto`) and `target_lang`. Auto-detection applies to text translation only; scanner source stays English.

For USB testing:

```sh
adb reverse tcp:8088 tcp:8088
```

Enter `http://127.0.0.1:8088` in the debug app's Settings → Backend address. For a release use an HTTPS URL; build-time defaults can be set with `SCIOBRAILLE_BACKEND_URL`. No translation API key belongs in Android. Existing desktop/USB scripts remain available.

## Translation configuration

Set environment variables **before starting the backend**. A `.env.example` documents them; the app does not load `.env` automatically. Never put real keys into Git.

| Provider | Configuration | Costs / limits |
|---|---|---|
| Disabled (default) | `TRANSLATION_PROVIDER=disabled` | English passthrough only online; installed Android models still translate locally |
| Google Cloud Translation v2 | `TRANSLATION_PROVIDER=google`, `TRANSLATION_API_KEY` | Official API; billing, quotas and supported language set belong to your account. Broad coverage, no key in APK |
| LibreTranslate | `TRANSLATION_PROVIDER=libretranslate`, `LIBRETRANSLATE_URL`, optional `TRANSLATION_API_KEY` | Self-hostable open-source service; compute/hosting costs. Only installed English→target pairs are advertised |
| Legacy community adapter | `TRANSLATION_PROVIDER=community` | Explicit evaluation-only option retained from the prototype; unofficial web adapter, no reliability guarantee. Not suitable as the production default |

Provider failures return an error and never relabel source text as a successful translation. The UI preserves the original. Language availability is fetched from the provider and cached for an hour. Google/Libre requests have timeouts and bounded translation concurrency. API tests use controlled provider contracts, clearly separated from live translation smoke tests.

## Offline behavior

- **Offline only:** uses bundled real TFLite inference; recognition/translation do not call the backend. English history and lessons stay local.
- **Auto:** tries device inference first; uncertain or missing results can use the backend. Network failures back off for 30 seconds while device recognition remains available.
- **Online preferred:** tries the backend, falling back to the device if unavailable.
- In Languages, long press a supported language → Download offline model. Downloads are explicit and need connectivity. Later translation checks installed models and never silently downloads during scanning. Delete individual models from the same menu.
- Native TTS selects an appropriate installed voice. Offline only requires an offline voice. Speech pauses on app backgrounding/audio focus loss; background playback is not implemented. Engines without word-range callbacks may resume from the current chunk rather than the exact word.

## What is preserved

Real model weights, YOLO inference/preprocessing, CameraX, the TFLite detector, HTTP/WebSocket APIs, local Room learning data, 57 English lessons across six levels, exercises and progress, Braille Studio, existing text/Braille tools, haptic/audio learning and exports. Local lessons no longer depend on an unimplemented payment flow. Prototype school/cloud sync endpoints are **disabled by default** because their original authentication accepts every request. `BRAILLE_ENABLE_LMS_API=development` restores them only for isolated development. Cloud sync needs proper per-user authentication/authorization before public use.

## Verification and remaining work

[Audit](docs/REPOSITORY_AUDIT_2026-11-05.md) · [Architecture](docs/ARCHITECTURE.md) · [Capability status](docs/CAPABILITY_STATUS.md) · [Verification report](docs/VERIFICATION.md) · [Device acceptance procedure](docs/DEVICE_ACCEPTANCE.md)

The three available labeled physical photographs are a small, non-independent regression set. They do not justify a high-accuracy production claim. No retraining or new quantization has been claimed. General perspective correction, arbitrary rotation, reliable punctuation/numbers/contractions and non-English Braille need suitable data/models and validation. Native offline inference, PDF export and an actual downloaded Tamil translation model passed emulator checks. Physical Android camera/latency/memory/battery, TalkBack usability, language/model quality beyond that smoke test, real device speech and release-signing validation remain explicit release gates.

UI copy and lessons remain primarily English; Unicode translation output and speech can use other languages. Older project reports describe historical builds and are superseded by this README and the linked verification report.
