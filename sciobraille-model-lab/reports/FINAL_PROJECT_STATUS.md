# Sciobraille Final Project Status

Date: 2026-09-19

## 1. Project Architecture

Sciobraille is a Kotlin native Android app using programmatic Android Views, CameraX, OkHttp WebSockets, Room, LiteRT, Android TTS, and local haptics. FastAPI serves scanner and LMS endpoints. Backend scanner uses Ultralytics YOLO PT inference. Backend LMS persistence uses SQLite. Scanner history uses guarded SharedPreferences JSON with a 50-entry limit.

## 2. Final Production Model

Backend model: `sciobraille-scanner/backend/model/best.pt`

- Architecture: YOLOv8s object detector
- Classes: 26, exactly `0=a` through `25=z`
- Input: 640 x 640
- Size: 22,537,258 bytes
- SHA256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- Backend settings: confidence 0.50, IoU 0.50, duplicate IoU 0.70, bilateral preprocessing, TTA enabled
- Accuracy source: `raw_text` only

## 3. V1 Optimized Model

`sciobraille-model-lab/models/v1_optimized/best.pt` is byte-identical to the production model. Conservative fine-tuning candidates did not beat its frozen-benchmark raw CER, so the original checkpoint plus optimized inference was selected.

V1 validation metrics: precision 0.9572, recall 0.9086, mAP50 0.9452, and mAP50-95 0.7506.

## 4. V2 Master Model

V2 model is not available. `models/v2_master/best.pt` does not exist. The validated Master V2 dataset exists and is ready for future training.

## 5. Model Hashes

- Production PT and V1 PT: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- Android TFLite: `9f6c45865ed2421041e8e46c865604ef953987382336c92bca91092d8eb5f4ad`
- Previous production rollback PT: same production hash; rollback metadata remains under `backend/model/rollback/`.

## 6. Dataset Used

V1 retains the Prabh merged lineage: 1,614 images and labels. Master V2 contains 1,784 unique retained images and 99,352 boxes after deduplication from 5,001 candidates. Split is 1,440 train, 165 validation, and 179 internal test. Sources contribute 1,414 Prabh, 143 Sangam, and 227 Asmitha images. V2 has not been trained.

## 7. End-to-End Benchmark

Frozen benchmark contains three physical phone-camera samples. Metrics use raw recognition output only.

- Backend PT: CER 0.3520, WER 0.4643, character accuracy 0.6480, word accuracy 0.5357, exact match 0.0000.
- Android TFLite artifact: same recognition metrics and raw output on all three samples.
- Backend Windows latency: average 270.94 ms, median 188.64 ms in repeated benchmark inference.
- TFLite Windows latency: average 581.40 ms, median 490.38 ms. This is not phone latency.

One orientation fails completely. Two readable images have one missing character each. Benchmark is too small for production accuracy claims.

## 8. Backend Status

Healthy for local prototype use. Root, `/health`, `/api/health`, `/api/scan-frame`, and `/ws/scan` work. Invalid input handling, upload limits, stateless POST behavior, named-session isolation, WebSocket isolation, and worker-thread inference are tested.

## 9. Android Status

Kotlin compilation, resources, CameraX, Room/KSP, OkHttp, LiteRT, debug packaging, release bundling, and lint pass. Debug backend URL targets `http://192.168.1.7:8088`. Release URL remains an HTTPS placeholder.

## 10. Online Scanner Status

Real local HTTP and WebSocket transport tests succeeded. Both returned:

```text
jaihind
india
sciobraille
isually impaired
great project
```

Corrected text restored `visually`. Raw text remained unchanged. Flip override worked. Android reconnect and five-second stale-socket fallback compile, but require final phone testing.

## 11. Offline Scanner Status

Android TFLite artifact loads and matches backend raw output on all three frozen samples in desktop runtime testing. Android preprocessing, class-agnostic duplicate removal, reading order, spacing, mirror handling, and stabilization are implemented. Physical-phone latency and memory behavior remain unmeasured.

## 12. LMS Status

Six levels are present: Dot Explorer, Letter Builder, Letter Recognition, Word Reading, Grade 2 Contractions, and Scan and Learn. English curriculum seed contains 57 deterministic lesson IDs. Room entities, DAOs, repository, progress, scores, streaks, milestones, entitlement gates, offline-first sync state, and scan-practice flow compile and have logic-level tests. Full device interaction remains unverified.

## 13. TTS Status

Shared LMS audio manager and scanner TTS paths are present with readiness checks, lifecycle stop behavior, and unavailable-engine handling. Device voice quality and rotation behavior need manual testing.

## 14. History Status

Stable scans save locally, duplicate consecutive text is suppressed, malformed records are skipped safely, and history is limited to 50 entries. Read, Copy, and Share actions are labeled. Device share-sheet behavior remains unverified.

## 15. Tests Passed

- Backend Pytest: 28 passed.
- Android JVM tests: 14 passed across 5 suites.
- Android lint: successful, zero errors.
- Python compile: successful for scanner, LMS API, and standalone inference.
- SQLite integrity: `ok`.
- Real HTTP scan: passed.
- Real WebSocket scan and flip override: passed.
- Online/offline raw-output comparison: 3 of 3 matched.

## 16. Tests Failed

No application test failed. Global `pip check` fails because installed Roboflow and Typer versions conflict. One frozen benchmark image produces no detection in the selected orientation; this is a model/product limitation, not a test harness failure.

## 17. Build Status

- Debug APK: successful, 59,631,451 bytes, SHA256 `f93ea343bb045f5419ebb7f2a0cdbaa946782cf7217f187cde2cba739f0ce5d6`.
- Release AAB: successful, 32,494,895 bytes, SHA256 `45a6af66929a1c1e9abecdcc98f80ebdeb0432da2379b69145540243e575dc`.
- No Play Store upload or public deployment occurred.

## 18. Known Limitations

1. No physical Android device was available for this pass.
2. Benchmark has only three images.
3. V2 model is missing.
4. Automatic orientation selection is absent.
5. Model supports only Grade 1 letters A-Z, not indicators or punctuation.
6. Release backend URL is not configured.
7. Fresh model exports did not meet the recognition gate.
8. Android lint has 199 non-blocking warnings, primarily hardcoded programmatic strings.
9. Optional speech recognition, Challenge mode, PDF certificates, payments, and school-code verification are placeholders.

## 19. Security Limitations

LMS authentication is not implemented. Current dependency accepts all requests. Never expose this backend publicly. Add verified identity, authorization, TLS, rate limits, and per-user/class access control before deployment. Local signing properties are ignored now; rotate credentials if they were ever shared.

## 20. Recommended Future Improvements

1. Run full camera, TalkBack, TTS, haptic, offline latency, and process-restart tests on at least two Android devices.
2. Expand frozen benchmark to 50-100 independent category-labeled physical images.
3. Train and evaluate V2 Master without changing the frozen benchmark.
4. Add automatic orientation selection with a deterministic confidence gate.
5. Add verified LMS authentication and configure a real HTTPS endpoint.
6. Resolve Roboflow/Typer environment conflict in a locked virtual environment.
7. Move programmatic UI strings into Android resources and migrate camera permission handling to Activity Result API.

## Final Decision

**B. PROTOTYPE READY WITH KNOWN LIMITATIONS**

Core backend, online transport, offline artifact, Android build, LMS structure, persistence contracts, and regression tests work locally. Physical-device usability, public security, V2, release networking, and a release-scale benchmark remain incomplete.
