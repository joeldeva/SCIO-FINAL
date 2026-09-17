# Sciobraille Play Production Checklist

## App Scope

- Live physical Braille scanning with English output.
- BrailleEye LMS with six offline-first learning levels.
- Local learner progress, milestones, certificates, premium gating, and school dashboard/reporting foundations.
- English curriculum is implemented. Hindi, Tamil, and Kannada are structured placeholders until verified Braille mappings are added.

## Backend

- Deploy `backend/scanner_api.py` behind HTTPS before public release.
- Keep `backend/model/best.pt` on the server.
- Expose:
  - `GET /api/health`
  - `POST /api/scan-frame`
  - `WS /ws/scan`
- Expose LMS sync/report APIs from `backend/LMS_API.md`.
- Add real authentication and authorization before enabling school dashboards or cloud sync publicly.

## Android Release

- Package id: `com.sciobraille.scanner`
- Configure `SCIOBRAILLE_BACKEND_URL` in `android/gradle.properties` or CI.
- Release builds disable cleartext traffic.
- Do not put API keys in the APK.
- Replace placeholder backend URL before Play upload.
- Use the generated upload keystore or replace it with your official Play upload key.
- Store upload signing values in `android/local.properties` or CI environment variables.
- See `RELEASE_SIGNING.md`.
- Build verification:
  - `:app:testDebugUnitTest`
  - `:app:assembleDebug`
  - `:app:bundleRelease`

## Play Store Disclosures

- Camera permission: used to scan Braille pages.
- Internet: sends captured frames to the Sciobraille backend for recognition.
- Network state: used to show/schedule sync state safely.
- Vibration: optional lesson haptics.
- TTS: speaks recognized text locally.
- Local LMS progress: lessons, answers, scores, streaks, milestones, and certificates are stored on device.
- Cloud sync, school dashboards, reports, and premium access need real account/auth infrastructure before public launch.
- Publish a privacy policy explaining camera-frame processing and LMS progress handling.
- Use `PRIVACY_POLICY_DRAFT.md` as the starting text.
- Use `DATA_SAFETY.md` for the Play Console data safety form.
- Use `PLAY_STORE_METADATA.md` for the first listing draft.
- Add a v2 training task for `MODEL_CLASS_EXPANSION.md`; the current model is
  still a 26-class `a-z` detector.
- Validate the packaged TFLite fallback on real Android hardware before relying
  on it as a Play Store offline mode.

## Required Manual Checks Before Production Track

- Install the debug APK on at least one real Android phone.
- Test scanner camera permission, backend unavailable message, and successful backend scan.
- Test Learn tab levels 1-6, progress persistence after app restart, TTS, and haptics.
- Test TalkBack reading order on Scanner, Learn, Progress, Upgrade, and Certificates.
- Replace the placeholder backend URL with a production HTTPS URL.
- Put a published privacy policy URL into the Play Console listing.
- Back up the upload keystore and passwords outside the project folder.

## Release Artifacts

- Debug APK: `releases/SciobrailleScanner-debug.apk`
- Release AAB: `releases/SciobrailleScanner-release.aab`
