# Sciobraille Play Production Checklist

## App Scope

- Live physical Braille scanning with English output.
- BrailleEye LMS with six offline-first learning levels.
- Local learner progress, milestones, certificates, premium gating, and school dashboard/reporting foundations.
- English curriculum is implemented. Hindi, Tamil, and Kannada are structured placeholders until verified Braille mappings are added.

## Offline Release Architecture

- The normal debug and release variants use bundled `best_int8.tflite`.
- Camera and gallery scans run on-device after horizontal-flip evaluation.
- The natural orientation is also evaluated and selected only when stronger.
- Room and SharedPreferences store progress and history locally.
- FastAPI and LMS sync endpoints are not called by the Play release.
- Keep all LMS backend routes private until real authentication exists.

## Android Release

- Package id: `com.sciobraille.scanner`
- Release builds disable cleartext traffic.
- Do not put API keys in the APK.
- Use the generated upload keystore or replace it with your official Play upload key.
- Store upload signing values in `android/local.properties` or CI environment variables.
- See `RELEASE_SIGNING.md`.
- Build verification:
  - `:app:testDebugUnitTest`
  - `:app:assembleDebug`
  - `:app:bundleRelease`

## Play Store Disclosures

- Camera permission: used to scan Braille pages.
- Internet: downloads optional ML Kit translation language models and opens the privacy policy.
- Network state: supports safe optional model-download behavior.
- Vibration: optional lesson haptics.
- TTS: speaks recognized text locally.
- Local LMS progress: lessons, answers, scores, streaks, milestones, and certificates are stored on device.
- Cloud sync, school dashboards, reports, premium billing, and public accounts are disabled.
- Optional model contributions require transcript review and explicit consent;
  no scanner image is uploaded automatically.
- Publish the offline privacy policy from repository `/docs` with GitHub Pages.
- Use `PRIVACY_POLICY_DRAFT.md` as the starting text.
- Use `DATA_SAFETY.md` for the Play Console data safety form.
- Declare optional contribution photos and corrected text consistently with the
  public privacy policy.
- Use `PLAY_STORE_METADATA.md` for the first listing draft.
- Add a v2 training task for `MODEL_CLASS_EXPANSION.md`; the current model is
  still a 26-class `a-z` detector.
- Validate the packaged TFLite model on several real Android phones.

## Required Manual Checks Before Production Track

- Install the debug APK on at least one real Android phone.
- Test scanner permission, camera/gallery scanning, horizontal orientation handling, and no-internet behavior.
- Test Learn tab levels 1-6, progress persistence after app restart, TTS, and haptics.
- Test TalkBack reading order on Scanner, Learn, Progress, Upgrade, and Certificates.
- Put a published privacy policy URL into the Play Console listing.
- Back up the upload keystore and passwords outside the project folder.

## Release Artifacts

- Debug APK: `releases/SciobrailleScanner-debug.apk`
- Release AAB: `releases/SciobrailleScanner-release.aab`
