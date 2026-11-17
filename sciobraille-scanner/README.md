# Sciobraille Scanner

## Multilingual scan speech

Scanner preserves raw, recognized, corrected, and translated text separately. The Play release uses Google ML Kit on-device translation and never sends recognized text to the Sciobraille backend. ML Kit downloads each selected language model before first use; downloaded models then work offline. Translated text uses an Android TTS voice matching the selected language. English recognition and saved source text remain available if translation or a TTS voice is unavailable.

Production-focused Android scanner built only from the local `BRAILLEVISION`
folder.

## Product Scope

Sciobraille combines three product areas:

1. **Offline Braille Scanner**: capture physical, handwritten, or embossed Braille and receive English text from the bundled V2 TFLite model.
2. **BrailleEye LMS**: an audio-first, accessible Braille learning path with local progress, milestones, and school-ready reporting contracts.
3. **Accessible Braille Tools**: Grade 1 text-to-Braille conversion, visual cells, tactile and haptic reading, printed-page OCR, translation, Smart Assist, and learner profiles.

The scanner remains usable for every account. The LMS is designed for learners, schools, and teachers without changing the scanner flow.

## Structure

- `backend/` - FastAPI scanner service using `model/best.pt`.
- `android/` - minimal native Android/Kotlin app.

## Optional Development Backend

```powershell
cd backend
python scanner_api.py
```

The backend is retained for model engineering and `v2Test` builds. The Play release does not require or call it. It exposes:

- `GET /api/health`
- `POST /api/scan-frame`
- `WS /ws/scan`
- `POST /api/translate`

The Android scanner always evaluates a horizontally mirrored frame locally. It
also evaluates natural orientation and selects it only when its confidence and
text structure clearly beat the mirrored result. No public image-flipping site
or Sciobraille server receives camera data.

Final V2 mobile inference uses confidence `0.25`, class-agnostic duplicate IoU
`0.70`, 640x640 letterbox preprocessing, and the canonical `a-z` class order.
A Scan tap captures one frame immediately, runs on-device inference, displays
one final result, and stops automatically. Tap Scan again for a new result.

The compact **Photo** action can capture through the camera or choose an image
from the device. Both paths use the same on-device orientation and recognition
pipeline.

## Android

Normal debug and release builds are offline-only. Configure
`SCIOBRAILLE_V2_BACKEND_URL` only when building the separate `v2Test` engineering
variant.

### USB Backend Connection

Only the `v2Test` engineering variant connects to `http://127.0.0.1:8000`. With the phone connected
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

Lessons, scores, milestones, certificates, and progress are stored locally in
Room. Scanner recognition also runs locally. Cloud LMS synchronization is
disabled in version 1.2.0.

### Premium And School Readiness

The complete local curriculum is unlocked in version 1.2.0. The account,
premium, school dashboard, and report contracts remain future architecture and
are not enabled in the Play release.

No payment, school-code verification, or authentication provider is implemented yet. School codes are retained only for later verified activation. The backend has database and API foundations for schools, teachers, students, classes, analytics, and CSV reports. **Do not expose the prototype LMS API publicly:** its authentication dependency currently accepts every request. Production deployment must add real authentication and authorization.

### Accessibility

LMS controls use text labels, TalkBack descriptions, TTS, optional haptics, and large touch targets. Display-only Braille cells provide a concise cell description; interactive cells expose individual dots. See [ACCESSIBILITY_QA.md](ACCESSIBILITY_QA.md) for the release QA audit and remaining device-testing recommendations.

## Verified Artifacts

- Debug APK: `releases/Sciobraille-1.2.0-offline-debug.apk`
- Signed release AAB: `releases/Sciobraille-1.2.0-play.aab`.

The release manifest uses `android:usesCleartextTraffic="false"`.

## Current Verification

Current integrated verification:

- Android unit tests: 37 passed.
- Backend tests: 31 passed.
- Debug APK build: passed.
- Signed Play AAB build and signature verification: passed.
- Release lint: zero errors.
- V2 model bytes and class ordering remain unchanged.

Desktop TFLite smoke checks use the same flip/orientation, confidence, NMS, and
text reconstruction rules as Android. Representative raw outputs include:

```text
SSN INVENTE NOT FLIPPED.jpeg -> ssn invente

test sciobraille.jpeg ->
jaihf d
india
sciobraille
visually impaired
greaq project
```

`Sri Sairam  noramal.jpeg` currently reads `iram`, and `DMI.jpeg` has no
detections. These are model-accuracy limitations, not transport failures; the
Play listing must not claim perfect recognition.

Backend verification:

- routes include `/api/health` and `/api/scan-frame`
- `ok=True`
- `stable=False` on the first frame and `stable=True` after a repeated matching frame
- detections: `50`
- mean confidence: approximately `0.86`

## Before Play Upload

- Publish `docs/privacy-policy.html` using GitHub Pages and use its URL in Play Console.
- Upload `releases/Sciobraille-1.2.0-play.aab` to Play internal testing.

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
