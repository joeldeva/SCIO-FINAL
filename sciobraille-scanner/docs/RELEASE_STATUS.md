# Sciobraille Release Status

Last updated: 2026-06-24

## Completed Locally

- Android package id is `com.sciobraille.scanner`.
- Debug APK builds successfully.
- Release AAB build path is configured.
- Release cleartext traffic is disabled.
- Upload keystore exists locally at `C:/Users/devaj/.sciobraille/keystores/sciobraille-upload.jks`.
- Release signing values are stored in ignored `android/local.properties`.
- Signed release AAB builds successfully with R8 minification enabled.
- Release manifest verification:
  - `versionCode=1`
  - `versionName=1.0.0`
  - `android:usesCleartextTraffic=false`
  - permissions: Camera, Internet, Network State, Vibration
- Scanner API contract exists: health, frame scan, WebSocket scan.
- LMS levels 1-6 are implemented in the Android app.
- LMS progress is local-first with Room.
- LMS sync manager fails safely when backend/auth is unavailable.
- Backend LMS curriculum, progress, score, analytics, school, and CSV report contracts exist.
- Accessibility QA document exists.
- Data safety, privacy policy, Play checklist, and Play metadata drafts exist.

## Current Artifacts

```text
releases/SciobrailleScanner-debug.apk
SHA256: 5F1A45E4C42170DBC230C1343C87CE57A94D9AB58554B907508FEA67038A98A6
Size: 47,396,782 bytes

releases/SciobrailleScanner-release.aab
SHA256: 58D24EF7D89BB2F7BE18841782E8521696F7B0C0C651D5E92083C11D29A0249D
Size: 31,023,872 bytes
```

Checksums are also stored in `releases/CHECKSUMS_SHA256.txt`.

## Must Be Done Before Public Play Upload

- Replace `SCIOBRAILLE_BACKEND_URL` with a real HTTPS backend URL.
- Deploy the backend behind HTTPS.
- Add real authentication and authorization before enabling cloud LMS sync,
  school dashboards, class analytics, reports, or premium account state.
- Publish the privacy policy and enter the final URL in Play Console.
- Back up the upload keystore and passwords outside this project.
- Run full real-device QA on at least one Android phone.
- Validate scanner accuracy under room light, side light, shadows, tilt, and
  different paper sizes.
- Confirm Play Console Data Safety answers against the final hosted backend.
- Create final store screenshots and icon/feature graphic assets.

## Recommended Release Gates

1. Local engineering gate: unit tests, debug build, release bundle.
2. Device QA gate: scanner, LMS, offline progress, TalkBack, TTS, haptics.
3. Backend gate: HTTPS, auth, privacy-safe logging, no persistent frame storage
   unless explicitly intended.
4. Play internal testing gate: upload AAB to internal testing, install from Play,
   verify camera and backend behavior.
5. Production gate: privacy policy live, data safety complete, support email
   live, screenshots approved, school/premium features either secured or hidden.
