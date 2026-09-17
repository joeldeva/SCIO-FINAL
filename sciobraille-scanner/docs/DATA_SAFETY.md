# Sciobraille Play Data Safety Draft

Use this as the starting point for the Google Play Console Data Safety form.
Confirm the final answers after the production backend and account system are
chosen.

## Data Collected Or Processed

### Camera Frames

- Purpose: Braille recognition.
- Collection: camera frames are sent to the Sciobraille scanner backend when
  scanning is active.
- Sharing: not sold. May be processed by infrastructure providers that host the
  backend.
- Retention: production backend should process frames transiently and avoid
  storing them unless the user explicitly opts into diagnostics.
- User control: user can stop scanning at any time.

### Recognition Output

- Purpose: display, speak, and save recognized Braille text/history.
- Storage: local device history. Cloud sync is optional and should require user
  account consent before public release.
- Sharing: not sold.

### LMS Progress

- Data: lesson completion, scores, answers, streaks, milestones, certificates,
  selected learning language, and sync status.
- Purpose: provide learning progress, offline use, certificates, premium access,
  school reports, and teacher dashboards.
- Storage: local Room database first. Backend sync is optional and must be
  authenticated before production use.

### Diagnostics

- Data: backend health, errors, performance logs.
- Purpose: reliability and support.
- Retention: configure production retention with least-necessary storage.

## Permissions

- Camera: required for live Braille scanning.
- Internet: required for backend scanner recognition and optional LMS sync.
- Network state: required to show safe sync status.
- Vibration: optional haptic feedback in lessons.

## Security Requirements Before Public Release

- Use HTTPS only for release backend traffic.
- Do not store API keys or secrets inside the APK.
- Protect LMS sync, reports, and dashboard endpoints with real authentication.
- Restrict school/class analytics to authorized teachers/admins.
- Publish a privacy policy URL in Play Console.
