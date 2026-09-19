# Sciobraille Scanner

Production-focused Android scanner built only from the local `BRAILLEVISION`
folder.

## Product Scope

Sciobraille combines two product areas:

1. **Live Braille Scanner**: point the phone camera at physical, handwritten, or embossed Braille to receive live English text output.
2. **BrailleEye LMS**: an audio-first, accessible Braille learning path with local progress, milestones, and school-ready reporting contracts.

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

Live frames are horizontally mirrored before model inference by default so
reverse-side Braille can be read without using an external image service. Set
`BRAILLE_FLIP_HORIZONTAL=false` to disable this globally. For an image that is
already flipped, call `POST /api/scan-frame?flip_horizontal=false` to prevent a
second mirror operation. Detection boxes are mapped back to the natural camera
preview coordinates.

Final V1 backend inference uses confidence `0.50`, model NMS IoU `0.50`,
class-agnostic duplicate IoU `0.70`, bilateral preprocessing, and TTA. The
Android fallback keeps confidence `0.35` because the frozen export benchmark
performed better at that threshold. Both paths use the same class order and
text reconstruction rules.

## Android

Configure `SCIOBRAILLE_BACKEND_URL` in `android/gradle.properties`.
Release builds must point to HTTPS. Debug builds allow local HTTP for testing.

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

### Offline And Sync

Lessons, scores, milestones, and progress are saved locally first. The scanner continues to use its existing backend plus offline fallback. Cloud LMS sync is optional and does not delete local data on failure.

For production sync, configure an HTTPS backend with `SCIOBRAILLE_BACKEND_URL`. Free users keep local progress; cloud sync is a premium capability.

### Premium And School Readiness

Free access includes the scanner, Dot Explorer, letters A-E, one recognition practice session, and local progress. Premium or school accounts unlock the full curriculum, scanner learning explanations, cloud sync, reports, and school dashboard support.

No payment, school-code verification, or authentication provider is implemented yet. School codes are retained only for later verified activation. The backend has database and API foundations for schools, teachers, students, classes, analytics, and CSV reports. **Do not expose the prototype LMS API publicly:** its authentication dependency currently accepts every request. Production deployment must add real authentication and authorization.

### Accessibility

LMS controls use text labels, TalkBack descriptions, TTS, optional haptics, and large touch targets. Display-only Braille cells provide a concise cell description; interactive cells expose individual dots. See [ACCESSIBILITY_QA.md](ACCESSIBILITY_QA.md) for the release QA audit and remaining device-testing recommendations.

## Verified Artifacts

- Debug APK: `releases/SciobrailleScanner-debug.apk`
- Release AAB: `releases/SciobrailleScanner-release.aab`

The release manifest uses `android:usesCleartextTraffic="false"`.

## Current Verification

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
- Offline fallback: `docs/OFFLINE_FALLBACK.md`
- Prototype references: `docs/prototype/`
- Play checklist: `docs/PLAY_PRODUCTION_CHECKLIST.md`
- Privacy policy draft: `docs/PRIVACY_POLICY_DRAFT.md`
- Play data safety draft: `docs/DATA_SAFETY.md`
- Play Store metadata draft: `docs/PLAY_STORE_METADATA.md`
- Release status: `docs/RELEASE_STATUS.md`
- LMS API and school reports: `backend/LMS_API.md`
- LMS accessibility QA: `ACCESSIBILITY_QA.md`
