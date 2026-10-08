# Sciobraille Workspace Cleanup Report

Date: 2026-10-03

## Production files protected

- `sciobraille-scanner/backend/model/best.pt`
- `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite`
- Android and backend source code, tests, configuration, and documentation
- `sciobraille-scanner/releases/Sciobraille-v1.1.9-USB.apk`
- V1 rollback checkpoint and rollback INT8 model
- `sciobraille-model-lab/datasets/master_v2`
- Canonical V1 and V2 model folders
- Training, evaluation, benchmark, provenance, and audit assets

## Removed

- Android build output and local Gradle/IDE caches
- Python test and bytecode caches
- Two rejected Master V2 build directories
- Root validation `runs` output
- Obsolete `yolo26n.pt` starter weight
- Duplicate calibration arrays
- Stale handoff and full-file-manifest files
- One exact duplicate root test image
- APK versions 1.1.4 through 1.1.7
- Redundant backend ONNX, SavedModel, Float32/Float16 TFLite, duplicate quantized exports, and obsolete Model A
- Intermediate V1 archive epoch and `last.pt` checkpoints; each run's selected `best.pt` remains
- 50 verified remote Git LFS cache objects
- Redundant source dataset copies from Prabh, Sangam, Asmitha, and the unlabeled Siddhant sample set
- Archived Prabh merged-dataset ZIP

Old source-project Git histories remain preserved. Master V2 provenance retains source paths, hashes, original splits, and mappings. Non-selected V2 experiment checkpoints remain available for research and were not required by production.

## Retained production dataset

Sciobraille V2 uses the repository's single canonical dataset, `sciobraille-model-lab/datasets/master_v2`, created from:

| Source | Candidate images | Retained unique images |
|---|---:|---:|
| Prabh merged | 1,614 | 1,414 |
| Sangam Braillie | 2,062 | 143 |
| Asmitha | 1,325 | 227 |
| **Total** | **5,001** | **1,784** |

Master V2 split:

- Train: 1,440 images
- Validation: 165 images
- Internal test: 179 images
- Bounding boxes: 99,352
- Classes: 26 (`a` through `z`)
- Label validation: 1,784 usable images, 0 errors, 0 warnings

Siddhant's dataset is not used by V2 because its 14 images have no YOLO labels.

## Verification

- Backend tests: 31 passed
- Android JVM tests: 35 passed
- Android debug APK build: successful
- Built APK SHA256 matched retained `Sciobraille-v1.1.9-USB.apk`
- Master V2 label validation: 1,784 images, 99,352 boxes, zero errors
- Frozen physical benchmark image was copied into the repository and its path made portable
