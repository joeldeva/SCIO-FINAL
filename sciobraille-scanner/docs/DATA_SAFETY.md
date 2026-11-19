# Sciobraille Play Data Safety - Version 1.3.0

Use these answers only for the offline Play build produced from this commit.
Reassess them before enabling accounts, analytics, cloud sync, or a backend.

## Data Collection

Sciobraille does not automatically transmit Braille camera frames, selected
images, recognized text, scan history, learner profile, or LMS progress to the
developer. Core recognition and learning run on the device.

After a scan, the user may deliberately choose **Improve the model**, correct
the ground-truth text, approve a dedicated consent statement, choose private
training or public dataset scope, and
share a contribution ZIP through Android's share sheet. The package contains
the selected model-facing image, predicted boxes, raw model text, corrected
text, optional notes, model/app metadata, random contribution ID, and consent
record. It contains no account, advertising ID, or device identifier.

For a conservative Play Console declaration, disclose the following as
**optional, user-initiated collection** when a contribution is sent to the
developer:

- Photos: Braille training image.
- Other user-generated content: corrected transcript and optional notes.
- Purpose: app functionality and developer communications; describe model
  improvement/research in the privacy policy and reviewer notes.
- Processing: not ephemeral when the package is accepted for dataset review.
- Sharing: no sale or advertising; transfer is initiated by the user through
  Android's share sheet. A public dataset contribution may later make the
  reviewed image/text/annotations publicly available, but only after separate
  public-release consent and project review.
- Deletion: source contribution deletion can be requested by contribution ID.

Google ML Kit can contact Google to download an optional translation model.
Android TTS, speech recognition, and sharing are system/user-selected services;
their handling is governed by the selected provider. Confirm Play Console's
current SDK-specific disclosure guidance before submission.

## Local Data

- Scan history and recognized text: SharedPreferences.
- Lessons, progress, scores, streaks, milestones, and certificates: Room.
- Learner profile and accessibility preferences: SharedPreferences.
- Temporary captured images and contribution exports: app cache. Pending images
  are deleted when replaced or the app closes; exports are pruned after 24
  hours and may also be cleared by Android.

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
- Confirm the public privacy URL includes the contribution section and is live.
- Declare optional contribution photos/text and the optional public dataset
  release consistently in Play Console.
- Review the current Play Data Safety definitions in Play Console.
- Re-run this assessment whenever dependencies or network behavior change.
