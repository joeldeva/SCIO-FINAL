# Sciobraille Release Status

Last updated: 17 November 2026

## Local Engineering Status

- Version `1.2.0` (`versionCode 14`)
- Package `com.sciobraille.scanner`
- Target API 36, minimum API 26
- Offline V2 TFLite scanner active for camera and gallery
- Horizontal-flip evaluation and automatic orientation selection active
- Full local LMS enabled
- Local history, progress, TTS, haptics, milestones, and certificates enabled
- Cloud sync, public backend use, billing, accounts, and school dashboards disabled
- Release signing configured outside Git
- Unit tests passing
- Release lint has zero errors
- Debug APK and signed release AAB produced

## Current Artifacts

- `releases/Sciobraille-1.2.0-offline-debug.apk`
- `releases/Sciobraille-1.2.0-play.aab`

See `releases/CHECKSUMS_SHA256.txt` and `docs/PLAY_RELEASE_HANDOFF.md`.

## External Steps Remaining

- Merge this branch into the default GitHub branch.
- Enable GitHub Pages from `/docs` and verify the privacy URL.
- Complete the Play Console listing and policy declarations.
- Upload the AAB to internal testing.
- Complete required tester/device QA and any closed-test requirement shown by
  the Play account.
- Promote to production only after real-device scanner and accessibility tests.

These steps require the owner's GitHub/Google Play account and cannot be
completed solely from the local repository.
