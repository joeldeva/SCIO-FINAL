# Device acceptance — execution pending

These are procedures to run on real Android devices, not passed tests. Record device, Android version, TTS engine/voices, model checksum and build commit. Test at least a small API 26 phone, a current mid-range phone, a tablet and an API 36 phone. Include TalkBack users in acceptance.

1. Fresh install: onboarding/skip, Home actions, permission grant/denial/permanent denial, Settings. A missing camera must leave photo translation available.
2. Camera: raised/reverse-side physical pages, multiline text and word gaps; portrait/landscape, flash absence, zoom, pause/resume/restart, screen off, navigation away, incoming calls. Ensure one inference at a time and no late result after pausing.
3. Import: camera capture/gallery, EXIF rotation, corrupt/oversized/HEIC input, empty page, large page, repeated photo and cancel. Correct reading manually; save/reopen must retain raw output and corrected text separately.
4. Translation: English→Tamil/Hindi/Telugu/Arabic/Chinese scripts, target change during a request, edit source during a request, provider errors/timeouts, server outage/recovery. No stale translation should attach to a new source/language.
5. Offline: in airplane mode with Offline only, real camera inference, local lessons/history and installed-model translation; missing-model/voice errors. Capture network traffic to verify no recognition/translation backend requests. Downloads are explicitly user initiated.
6. Speech: missing/matching voices, offline and network voices, pause/resume/replay/stop, long text, emoji, Bluetooth/headphones, audio focus loss and app background. Pause position may be chunk-level for engines without range callbacks.
7. History: auto-save only stable live reading, single photo saving, no repeated duplicate scan, translations in different languages, date/search filters, copy/share/reuse/delete/clear, restart and process death.
8. Learning: six levels, existing 57 English lessons, exercises, scores, unlocks and progress after app restart. Cloud sync must remain explicitly unavailable until secure accounts exist.
9. Accessibility: TalkBack traversal order/content, selected tab states, permission dialogs, language download actions, image result correction, speech controls, RTL output, font 200%, app extra-large, high contrast, dark/light and landscape. No clipped action label or focus trap is acceptable.
10. Performance: record end-to-end p50/p95 frame-to-text latency, peak memory, ANRs/crashes, 15-minute battery/thermal behavior and 30-minute repeated scan stability. Desktop inference times are not phone timings.

Release criteria must be agreed using representative independent physical Braille pages. Report CER/WER, missed cells/lines, confidence calibration and per-condition errors. Three repository photographs or detector mAP alone are not sufficient.
