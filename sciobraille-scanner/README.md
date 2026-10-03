# Sciobraille Scanner

## Multilingual scan speech

Scanner preserves raw, recognized, corrected, and translated text separately. Recognized English text first uses the existing FastAPI `/api/translate` endpoint, then Google ML Kit on-device translation if backend translation fails. Translated text uses an Android TTS voice matching the selected language. Supported targets are English, Hindi, Tamil, Telugu, Malayalam, Kannada, Spanish, French, German, Chinese, and Japanese. ML Kit downloads each language model before first local use. English recognition and saved source text remain available if translation fails. Each device must have the required Android TTS voice installed.

Production-focused Android scanner built only from the local `BRAILLEVISION`
folder.

## Product Scope

Sciobraille combines three product areas:

1. **Live Braille Scanner**: point the phone camera at physical, handwritten, or embossed Braille to receive live English text output.
2. **BrailleEye LMS**: an audio-first, accessible Braille learning path with local progress, milestones, and school-ready reporting contracts.
3. **Accessible Braille Tools**: Grade 1 text-to-Braille conversion, visual cells, tactile and haptic reading, printed-page OCR, translation, Smart Assist, and learner profiles.

The scanner remains usable for every account. The LMS is designed for learners, schools, and teachers without changing the scanner flow.

## Structure

- `backend/` - FastAPI scanner service using `model/best.pt`.
- `android/` - minimal native Android/Kotlin app.

## Backend

```powershell
cd backend
python scanner_api.py
```

The backend exposes:

- `GET /api/health`
- `POST /api/scan-frame`
- `WS /ws/scan`
- `POST /api/translate`

Each captured frame is horizontally mirrored inside Sciobraille immediately
before model inference. No public image-flipping website receives camera data.
Detection boxes are mapped back to the natural camera-preview coordinates
after text reconstruction.

Final V2 backend inference uses confidence `0.25`, model NMS IoU `0.45`,
class-agnostic duplicate IoU `0.70`, bilateral preprocessing, and no TTA. A
Scan tap captures one frame immediately and sends it to the configured backend.
The UI shows `Scanning` while the backend model runs, then locks one final
result and stops automatically. If the backend cannot be reached, the app shows
a connection error instead of substituting an offline-model result. Tap Scan
again to capture a new result.

The compact **Photo** action on the Scanner screen can either capture through
the existing camera flow or choose an image from the device. Selected images
are horizontally mirrored before backend inference and use the same backend-only
recognition with a clear connection error if the backend is unavailable.

## Android

Configure `SCIOBRAILLE_BACKEND_URL` in `android/gradle.properties`.
Release builds must point to HTTPS. Debug builds allow local HTTP for testing.

### USB Backend Connection

The USB debug APK connects to `http://127.0.0.1:8000`. With the phone connected
and USB debugging authorized, run `android/connect_usb_backend.bat`. It creates
an ADB reverse tunnel from device port `8000` to the laptop backend on port
`8088`. Wi-Fi and mobile data are not required. The tunnel must be recreated
after the phone or cable reconnects.

Use `android/build_cached_gradle.ps1` on this machine if `gradle` is not in PATH.

```powershell
cd android
powershell.exe -ExecutionPolicy Bypass -File .\build_cached_gradle.ps1 :app:testDebugUnitTest
powershell.exe -ExecutionPolicy Bypass -File .\build_cached_gradle.ps1 :app:assembleDebug
powershell.exe -ExecutionPolicy Bypass -File .\build_cached_gradle.ps1 :app:bundleRelease
```

## BrailleEye LMS

The Learn tab contains six levels:

1. Dot Explorer: learn the six Braille dot positions with large targets, audio, and haptics.
2. Letter Builder: learn Grade 1 English Braille letters A-Z.
3. Letter Recognition: identify Braille letter patterns in guided sessions.
4. Word Reading: decode starter words cell by cell.
5. Grade 2 Contractions: learn the first common contractions, with a structure ready for expansion.
6. Scan and Learn: use scanner output as real-world practice.

Shared LMS components:

- `BrailleCellView` for interactive and display-only Braille cells.
- `LmsAudioManager` for safe TTS and repeatable instructions.
- `LmsHapticManager` for optional haptic feedback with no-vibrator fallback.
- Room-backed `LmsRepository` for lessons, progress, scores, streaks, sync state, and milestones.

### Braille Tools

Open **Learn > Braille Tools** for:

- **Braille Studio**: converts English letters, capitals, numbers, spaces, line breaks, and common punctuation into Grade 1 Braille without inventing patterns for unsupported characters.
- **Visual and haptic reader**: browse cells, hear dot descriptions, and play, pause, or resume tactile cell sequences.
- **Tactile Explorer**: explore all six positions with distinct dot haptics and spoken active/inactive state.
- **Story Reader**: capture or select a printed page and recognize Latin text locally with ML Kit; TTS remains on-device.
- **Translation**: translates recognized text through the configured backend to Hindi, Tamil, Telugu, Malayalam, Kannada, Spanish, French, German, Chinese, or Japanese. Original text is retained when translation is unavailable.
- **Smart Assist**: Android speech recognition routes commands to the scanner, lessons, Studio, Story Reader, tactile explorer, progress, or learner profile.
- **Practice Library**: supplementary numbers, punctuation, functional labels, everyday words, directions, school words, and safety vocabulary with Room-backed completion.
- **Learner Profile**: stores name, optional age, goal, preferred learning mode, and learning language locally. Certificate names use this profile.

The six-level LMS unlock path remains unchanged. **Today's Practice** uses persisted question scores to prioritize attempted letters below 70% accuracy, then selects the next incomplete Letter Builder lesson.

### Offline And Sync

Lessons, scores, milestones, and progress are saved locally first. Scanner recognition requires the configured backend. Cloud LMS sync is optional and does not delete local data on failure.

For production sync, configure an HTTPS backend with `SCIOBRAILLE_BACKEND_URL`. Free users keep local progress; cloud sync is a premium capability.

### Premium And School Readiness

Free access includes the scanner, Dot Explorer, letters A-E, one recognition practice session, and local progress. Premium or school accounts unlock the full curriculum, scanner learning explanations, cloud sync, reports, and school dashboard support.

No payment, school-code verification, or authentication provider is implemented yet. School codes are retained only for later verified activation. The backend has database and API foundations for schools, teachers, students, classes, analytics, and CSV reports. **Do not expose the prototype LMS API publicly:** its authentication dependency currently accepts every request. Production deployment must add real authentication and authorization.

### Accessibility

LMS controls use text labels, TalkBack descriptions, TTS, optional haptics, and large touch targets. Display-only Braille cells provide a concise cell description; interactive cells expose individual dots. See [ACCESSIBILITY_QA.md](ACCESSIBILITY_QA.md) for the release QA audit and remaining device-testing recommendations.

## Verified Artifacts

- Debug APK: `releases/Sciobraille-Final.apk`
- Release AAB: not generated in this pass because local Play upload signing is not configured.

The release manifest uses `android:usesCleartextTraffic="false"`.

## Current Verification

Current integrated verification:

- Android unit tests: 23 passed.
- Backend tests: 31 passed.
- Debug APK build: passed.
- Scanner inference code and selected V2 model were not changed by the tools/LMS integration.

Known image:
`C:\Users\devaj\Downloads\test sciobraille.jpeg`

Verified raw scanner output:

```text
jaihind
india
sciobraille
isually impaired
great project
```

Verified corrected display output restores `visually impaired`. Benchmark accuracy always uses the raw output above.

Backend verification:

- routes include `/api/health` and `/api/scan-frame`
- `ok=True`
- `stable=False` on the first frame and `stable=True` after a repeated matching frame
- detections: `50`
- mean confidence: approximately `0.86`

## Before Play Upload

- Replace `SCIOBRAILLE_BACKEND_URL` with the real HTTPS backend URL.
- Sign the release through the Play upload/signing workflow.
- Publish a privacy policy covering camera frames sent to the backend.

Production notes:

- Backend deployment: `docs/BACKEND_DEPLOYMENT.md`
- Release signing: `docs/RELEASE_SIGNING.md`
- Model class expansion: `docs/MODEL_CLASS_EXPANSION.md`
- Historical offline prototype notes: `docs/OFFLINE_FALLBACK.md`
- Prototype references: `docs/prototype/`
- Play checklist: `docs/PLAY_PRODUCTION_CHECKLIST.md`
- Privacy policy draft: `docs/PRIVACY_POLICY_DRAFT.md`
- Play data safety draft: `docs/DATA_SAFETY.md`
- Play Store metadata draft: `docs/PLAY_STORE_METADATA.md`
- Release status: `docs/RELEASE_STATUS.md`
- LMS API and school reports: `backend/LMS_API.md`
- LMS accessibility QA: `ACCESSIBILITY_QA.md`
