# Sciobraille Remaining Work

V2 Master training, internal evaluation, exports, parity checks, and isolated Android test builds are complete. V1 remains the production choice because V2 has not beaten V1 on the available physical raw-text regression samples.

## Completed

- Master V2 dataset built with 1,784 retained images and 99,352 boxes.
- YOLOv8s and YOLO11s candidates trained for 30 epochs each.
- YOLOv8s selected as V2 by validation mAP50-95.
- Selected V2 evaluated once on the internal test split.
- PT, ONNX, Float32 TFLite, and INT8 TFLite artifacts exported and checked.
- V2 INT8 end-to-end parity checked against V2 PT.
- Separate `v2Test` Android variant built without replacing production assets.
- Final V1 phone APK rebuilt and signature verified.

## Required Before V2 Production Promotion

1. Collect 50-100 independent physical Braille phone captures.
2. Cover different documents, devices, lighting, shadows, blur, perspective, distance, line layouts, and raised/reverse sides.
3. Freeze exact raw ground truth and benchmark hashes before model comparison.
4. Confirm V2 improves raw CER and WER with statistical confidence and no major condition regressions.
5. Profile V2 INT8 latency and memory on representative Android devices.
6. Complete TalkBack, TTS, haptic, camera, reconnect, and long-running scan tests on real hardware.

## Known Model Gap

`DMI.jpeg` returns no detections from V1 or V2. It represents relief/orientation conditions absent from the retained training distribution. `Flipped DMI.jpeg` is readable, with V1 producing better raw text than V2. These images remain regression inputs and must not be copied into training data.

## Release Work

- Replace local HTTP backend configuration with a stable HTTPS endpoint.
- Create and protect a release signing key outside Git.
- Build and test a signed release AAB.
- Complete Play Store privacy, data-safety, accessibility, and device testing requirements.
