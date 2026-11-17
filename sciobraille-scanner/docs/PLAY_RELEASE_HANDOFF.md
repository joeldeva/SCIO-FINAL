# Sciobraille 1.2.1 Play Release Handoff

## Release Architecture

- Package: `com.sciobraille.scanner`
- Version code: `15`
- Version name: `1.2.1`
- Minimum Android: API 26
- Target Android: API 36
- Scanner: bundled V2 TFLite model, 640x640 input, classes `a-z`
- Scan transport: on-device only in debug and release variants
- Orientation: flipped inference always runs; natural orientation is selected
  only when its confidence and text quality are clearly stronger
- LMS: complete local curriculum enabled, Room-backed progress
- Cloud sync, accounts, billing, school dashboards, and public FastAPI calls:
  disabled in the Play release
- Training samples: optional local contribution ZIP after transcript review and
  explicit consent; never uploaded automatically

## Artifacts

- Play upload: `releases/Sciobraille-1.2.1-play.aab`
- Direct device QA: `releases/Sciobraille-1.2.1-offline-debug.apk`
- Model asset: `android/app/src/main/assets/best_int8.tflite`

SHA256:

- AAB: `547D9A1B83FFF6D49A5A981F6D7A8E4BF051B2E6E482A812B954E7993B4C1107`
- APK: `FCAE0144CB47716AC8C5AC82CB90845A6D82B0307413AB7F29F2BA5727A8EEE5`

The AAB is signed with the local upload key. The key and passwords are outside
Git. Back them up before uploading the first bundle to Play Console.

## Verified Locally

- Android unit tests: 39 passed
- Backend regression tests: 31 passed
- Release lint: passed with zero errors
- Debug APK: built
- Signed release AAB: built and JAR signature verified
- Release manifest: target API 36, cleartext disabled, no orientation lock,
  local-data backup disabled
- AAB contains `base/assets/best_int8.tflite`
- TFLite tensor shape: input `[1,640,640,3]`, output `[1,30,8400]`
- Class count/order: 26 classes, `0=a` through `25=z`
- Contribution importer: valid package accepted; duplicate image SHA256 rejected

## Play Console Steps Requiring The Account Owner

1. Merge this branch to the GitHub default branch.
2. In GitHub repository Settings > Pages, publish from the default branch
   `/docs` folder.
3. Confirm this URL opens publicly:
   `https://joeldeva.github.io/SCIO-FINAL/privacy-policy.html`.
4. Create the Play Console app using package `com.sciobraille.scanner`.
5. Enable Play App Signing and upload `Sciobraille-1.2.1-play.aab`.
6. Enter support email `devajoel8@gmail.com` and the privacy URL.
7. Complete Data Safety using `docs/DATA_SAFETY.md`.
8. Complete content rating, app access, ads, target audience, and store listing.
9. Add final phone screenshots, 512x512 icon, and 1024x500 feature graphic.
10. Run internal testing. New personal accounts may also need the current
    closed-testing requirement before production access.

## Mandatory Device QA Before Production

- Camera permission allow and deny flows
- Rear-camera Scan and Photo capture
- Gallery upload
- Front-side and reverse-side Braille
- No-internet scan, history, LMS, TTS, and app restart
- Low-memory/background/rotation behavior
- TalkBack reading order and large text
- Translation model download, then translation without internet
- Improve the model consent, ZIP creation, and share/cancel flows

## Known Model Limits

The detector recognizes lowercase English Grade 1 letters `a-z`. It does not
yet detect number/capital indicators, punctuation, or Grade 2 contractions.
Store claims must not describe it as complete literary Braille recognition.
Accuracy varies with lighting, focus, scale, embossing quality, and page angle.

## Backend Security Boundary

The FastAPI backend is retained for engineering. Its LMS authentication is a
placeholder and it must not be publicly exposed. The Play release does not call
that backend, so this does not block the offline release.
