# Sciobraille Play Data Safety - Version 1.2.0

Use these answers only for the offline Play build produced from this commit.
Reassess them before enabling accounts, analytics, cloud sync, or a backend.

## Data Collection

Sciobraille does not transmit Braille camera frames, selected images, recognized
text, scan history, learner profile, or LMS progress to the developer. Core
recognition and learning run on the device.

Google ML Kit can contact Google to download an optional translation model.
Android TTS, speech recognition, and sharing are system/user-selected services;
their handling is governed by the selected provider. Confirm Play Console's
current SDK-specific disclosure guidance before submission.

## Local Data

- Scan history and recognized text: SharedPreferences.
- Lessons, progress, scores, streaks, milestones, and certificates: Room.
- Learner profile and accessibility preferences: SharedPreferences.
- Temporary captured images: app cache, deleted after processing.

Users can clear local data in Android settings or uninstall the app.

## Permissions

- `CAMERA`: capture Braille and printed pages.
- `INTERNET`: download optional ML Kit language models and open the privacy
  policy. It is not required for core Braille recognition or lessons.
- `ACCESS_NETWORK_STATE`: allow optional language-model download behavior to
  fail safely.
- `VIBRATE`: optional learning haptics.

## Disabled In This Release

- Sciobraille accounts and authentication
- LMS cloud synchronization
- Teacher/school dashboards
- Advertising and analytics SDKs
- Public FastAPI communication

## Submission Checks

- Confirm the merged release manifest matches this document.
- Confirm the public privacy URL is live.
- Review the current Play Data Safety definitions in Play Console.
- Re-run this assessment whenever dependencies or network behavior change.
