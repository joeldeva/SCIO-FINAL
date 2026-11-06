# Capability and release status

This is an integrated development application using the existing project. Implemented behavior and production validation are separate. See [VERIFICATION.md](VERIFICATION.md) for executed checks.

| Capability | Implemented behavior | Remaining limitation |
|---|---|---|
| Live recognition | CameraX continuous analysis, real on-device detector and FastAPI fallback; pause/resume/restart, flash/zoom and stable results | Physical camera, battery, thermal and long-session checks pending |
| Image recognition | Capture/gallery, bounded decode, EXIF orientation, box overlay and corrections | Physical-device picker/capture checks pending |
| Reading order | Cell positions, row grouping, gaps and mild geometric deskew | Full perspective rectification and arbitrary rotation unsupported |
| Braille standards | Existing English a–z model; extensible capability registry | Numbers, punctuation, capital signs, Grade 2 and Bharati camera recognition unsupported |
| Translation | 133-language catalog, searchable native names/favorites/recents, Google/Libre provider adapters and installed ML Kit models | Actual availability depends on provider/model; all languages and meaning preservation are not validated |
| Offline translation | Explicit downloads/deletion, installed-model checks, backend disabled in Offline only; actual Tamil model download/local inference tested | Initial download needs internet; sample Tamil output omitted a source term; quality and other languages need review |
| Speech | Locale/voice selection, play/pause/resume/replay/stop, rate and audio focus | Voice availability and pause precision depend on engine; physical-device speech validation pending; no background playback |
| History | Local original/corrected/translated variants, search/date filter/delete/reuse/share | 50-record limit; no cloud synchronization |
| Learning | Existing six levels and 57 English lessons, Room progress, exercises, tactile tools and real PDF certificate export | Secure school accounts/cloud sync unavailable; PDF is not accessibility tagged |
| Screens | Native splash, onboarding, Home, scanner/results/photo import, languages, History, Learn, settings and Help connected | Primary UI/lesson language remains English |
| Accessibility | Native labels, large controls, light/dark/high contrast and adjustable text/speech; rendered large-text navigation checked | Human TalkBack/low-vision evaluation and full device matrix pending |
| Backend | Existing YOLO/FastAPI HTTP and WebSocket inference retained; input bounds, capabilities and bounded translation calls | Public HTTPS deployment, authentication/abuse controls and provider configuration required |
| Recognition quality | Existing weights preserved; real photo regression and uncertainty reporting | Significant errors on the small dataset; no retraining or accuracy gain claimed |
| Distribution | Verified debug APK, CI, development branch and build/signing guides | Production upload key, store release and physical-device acceptance outstanding |

A stable reading, successful provider response or completed build alone does not establish recognition accuracy, translation quality or assistive usability. Follow the [device checklist](DEVICE_ACCEPTANCE.md) before release.
