# LMS Implementation Plan

## Current App Structure

Project root:

```text
sciobraille-scanner/
  android/   Native Android scanner app
  backend/   Python scanner backend
  docs/      Product and deployment documentation
```

Android app root:

```text
sciobraille-scanner/android
```

Current Android architecture:

- Language: Kotlin.
- App module namespace/package: `com.sciobraille.scanner`.
- Main entry point: `app/src/main/java/com/sciobraille/scanner/MainActivity.kt`.
- UI style: programmatic Android Views in Kotlin. There are no XML screen layouts and no Jetpack Compose usage.
- Activity structure: single `ComponentActivity`.
- Navigation: custom bottom navigation built manually with `LinearLayout` and `TextView` items.
- Current tabs: `SCANNER`, `HISTORY`, `ABOUT`.
- Navigation state: `enum class AppTab` in `MainActivity.kt`.
- Database: no Room database. Scan history is stored as JSON in `SharedPreferences` under the `sciobraille` preference file.
- TTS/audio: Android `TextToSpeech`, initialized in `MainActivity`, using `Locale.US` and `QUEUE_FLUSH`.
- Camera: CameraX with `PreviewView`, `Preview`, `ImageCapture`, and `ProcessCameraProvider`.
- Networking: OkHttp WebSocket to the scanner backend.
- Offline model fallback: TensorFlow Lite model in `app/src/main/assets/best_int8.tflite`, used by `OfflineBrailleDetector`.

Existing source files:

```text
app/src/main/java/com/sciobraille/scanner/MainActivity.kt
app/src/main/AndroidManifest.xml
app/src/main/res/values/strings.xml
app/src/main/res/values/styles.xml
app/src/main/res/drawable/ic_launcher.xml
app/src/main/assets/best_int8.tflite
app/src/test/java/com/sciobraille/scanner/ResponseParserTest.kt
```

Current dependencies:

- `androidx.core:core-ktx`
- `androidx.activity:activity-ktx`
- `androidx.camera:*`
- `okhttp`
- `tensorflow-lite`
- JUnit and `org.json` for tests

There is no Navigation Component, no Fragment stack, no Compose runtime, no RecyclerView dependency, and no Room dependency.

## Scanner Flow

The scanner is currently implemented inside `MainActivity.kt` and should be treated as protected working code.

Important scanner sections:

- `buildScannerScreen()` builds the camera preview, Scan button, stats row, output card, and action buttons.
- `startCamera()` binds the back camera with CameraX.
- `startScanning()` opens the scanner WebSocket and starts the repeated capture loop.
- `scanLoop` captures frames every `350ms`.
- `captureAndScan()` saves a temporary JPEG frame, sends it over WebSocket, and falls back to local TFLite if the socket is unavailable.
- `openScanSocket()` connects to `BuildConfig.SCIOBRAILLE_BACKEND_URL` converted to `/ws/scan`.
- `ScannerPayload.fromJson()` parses backend responses.
- `renderPayload()` updates the detection overlay, confidence stats, visible text, Braille preview, and history.
- `DetectionOverlayView` draws normalized bounding boxes over the camera preview.
- `OfflineBrailleDetector` runs the bundled TFLite model when backend scanning is unavailable.

Detected Braille text is produced by either:

1. Backend path: CameraX frame -> JPEG bytes -> OkHttp WebSocket -> backend YOLO scanner -> JSON response -> `ScannerPayload` -> `renderPayload()`.
2. Fallback path: CameraX frame -> temporary JPEG file -> `OfflineBrailleDetector.detect()` -> TFLite detections -> local reading-order decode -> `ScannerPayload` -> `renderPayload()`.

The scanner also adds stable readings to local history through `addHistoryIfNew()`.

## Bottom Navigation

Bottom navigation is custom, not library-based.

Relevant code:

- `buildUi()` creates `contentHost`, adds scanner/history/about screens, then adds `buildBottomNav()`.
- `buildBottomNav()` creates three text items: Scanner, History, About.
- `showTab(tab: AppTab)` toggles view visibility and stops active scanning when leaving the Scanner tab.
- `updateNav()` and `updateNavItem()` update selected tab styling.
- `AppTab` currently contains `SCANNER`, `HISTORY`, and `ABOUT`.

The LMS module should join this system carefully by adding one new tab and one new screen without changing scanner internals.

## Files To Modify

Minimal first LMS integration:

```text
android/app/src/main/java/com/sciobraille/scanner/MainActivity.kt
```

Expected safe changes in that file:

- Add `LEARN` to `AppTab`.
- Add `learnScreen` and `learnNav` fields.
- Add `buildLearnScreen()`.
- Add the screen to `contentHost` in `buildUi()`.
- Add a Learn nav item in `buildBottomNav()`.
- Update `showTab()` and `updateNav()` to include Learn.
- Keep the existing rule that scanning stops when leaving the Scanner tab.

Optional future modifications:

```text
android/app/src/main/res/values/strings.xml
android/app/build.gradle
```

Only modify `build.gradle` later if adding a real persistence layer, media playback library, or RecyclerView.

## Files To Create

Recommended package split before the LMS grows:

```text
android/app/src/main/java/com/sciobraille/scanner/learn/LearnModels.kt
android/app/src/main/java/com/sciobraille/scanner/learn/LearnRepository.kt
android/app/src/main/java/com/sciobraille/scanner/learn/LearnProgressStore.kt
android/app/src/main/java/com/sciobraille/scanner/learn/LearnViews.kt
```

Recommended static lesson data:

```text
android/app/src/main/assets/learn/grade1_lessons.json
```

Recommended tests:

```text
android/app/src/test/java/com/sciobraille/scanner/learn/LearnRepositoryTest.kt
android/app/src/test/java/com/sciobraille/scanner/learn/LearnProgressStoreTest.kt
```

For the first implementation, use JSON assets plus `SharedPreferences` progress storage. Do not add Room until lesson progress needs querying, syncing, or richer analytics.

## Risk Areas

- `MainActivity.kt` is large and currently owns scanner, history, about, TTS, camera, network, and fallback inference. LMS changes can accidentally break scanner lifecycle if they modify shared fields or `showTab()`.
- Leaving the Scanner tab intentionally calls `stopScanning("Stopped")`. LMS must preserve this behavior.
- CameraX resources and TFLite interpreter are lifecycle-sensitive. LMS code should not touch `startCamera()`, `captureAndScan()`, `OfflineBrailleDetector`, or `onDestroy()` except for clearly isolated future refactors.
- Bottom navigation uses equal weights. Adding a fourth tab may make labels cramped on small screens; use short label text such as `Learn`.
- No Room database exists. Introducing Room too early would add migration and schema risk without immediate need.
- TTS is shared with scanner output. LMS audio should reuse a small wrapper around the existing `TextToSpeech` instance or introduce a controlled `SpeechController`, not create competing TTS engines.
- Programmatic UI makes large feature additions harder to maintain. Keep LMS views isolated in helper files or a `learn` package instead of adding hundreds of lines directly into scanner logic.

## Step-by-Step LMS Build Plan

1. Add a lightweight Learn tab shell.
   - Add `AppTab.LEARN`.
   - Add `learnScreen` and `learnNav`.
   - Add `buildLearnScreen()` with static placeholder lessons.
   - Confirm Scanner, History, About still switch correctly.

2. Extract reusable speech behavior safely.
   - Add a tiny method or helper for speaking arbitrary learning text.
   - Keep scanner `speakOutput()` behavior unchanged.

3. Add lesson data model.
   - Create `LearnLesson`, `LearnExercise`, and `LearnProgress` data classes.
   - Store initial Grade 1 alphabet lessons in an asset JSON file.
   - Include Braille cell, English letter, word examples, and short practice prompts.

4. Add repository and progress storage.
   - Load lessons from `assets/learn/grade1_lessons.json`.
   - Store completed lesson IDs and quiz scores in `SharedPreferences`.
   - Keep storage separate from scanner history keys.

5. Build first LMS screens.
   - Lesson list.
   - Lesson detail.
   - Practice/quiz screen.
   - Progress summary.
   - Keep all LMS UI in a `learn` package or clearly separated builder functions.

6. Add accessibility and audio.
   - Speak lesson instructions.
   - Speak letters/words/examples.
   - Add larger touch targets and clear completion feedback.

7. Add tests.
   - Unit test lesson JSON parsing.
   - Unit test progress serialization.
   - Keep existing `ResponseParserTest` unchanged.

8. Regression test scanner.
   - Build app.
   - Open Scanner tab.
   - Start/Stop scanning.
   - Verify camera preview remains active.
   - Verify backend WebSocket output still renders boxes and text.
   - Switch to Learn and back to Scanner; scanning should stop cleanly and restart on demand.

## Non-Goals For This First Step

- Do not rewrite the scanner.
- Do not replace programmatic Views with Compose.
- Do not introduce Navigation Component yet.
- Do not add Room yet.
- Do not change backend scanner APIs.
- Do not rename package IDs.
- Treat any `brailleeye` naming in future source/prototypes as Sciobraille branding.
