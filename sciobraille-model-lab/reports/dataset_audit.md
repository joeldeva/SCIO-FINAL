# Sciobraille Dataset Audit

Read-only audit. No merge. No training. No production model changes.

## Datasets Found

### asmitha__dataset

- data.yaml: `asmitha/dataset/data.yaml`
- root: `asmitha/dataset`
- images: 1325
- labels: 1325
- annotation rows: 21439
- valid 5-column bounding boxes: 21355
- split images: train=1016, val=209, test=100
- split labels: train=1016, val=209, test=100
- split annotations: train=16502, val=3381, test=1556
- split boxes: train=16418, val=3381, test=1556
- classes: `{"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F", "6": "G", "7": "H", "8": "I", "9": "J", "10": "K", "11": "L", "12": "M", "13": "N", "14": "O", "15": "P", "16": "Q", "17": "R", "18": "S", "19": "T", "20": "U", "21": "V", "22": "W", "23": "X", "24": "Y", "25": "Z"}`
- class IDs seen: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- top dimensions: 640x640=1096, 640x288=197, 640x467=2, 640x344=1, 640x452=1, 640x238=1, 640x278=1, 640x565=1
- SHA256 image rows: 1325
- errors: 84

### braille_hackathon_siddhant__dataset

- data.yaml: `braille_hackathon_siddhant/dataset/data.yaml`
- root: `braille_hackathon_siddhant/dataset/dataset`
- images: 0
- labels: 0
- annotation rows: 0
- valid 5-column bounding boxes: 0
- split images: train=0, val=0, test=0
- split labels: train=0, val=0, test=0
- split annotations: train=0, val=0, test=0
- split boxes: train=0, val=0, test=0
- classes: `{"0": "a", "1": "b", "2": "c", "3": "d", "4": "e", "5": "f", "6": "g", "7": "h", "8": "i", "9": "j", "10": "k", "11": "l", "12": "m", "13": "n", "14": "o", "15": "p", "16": "q", "17": "r", "18": "s", "19": "t", "20": "u", "21": "v", "22": "w", "23": "x", "24": "y", "25": "z"}`
- class IDs seen: `[]`
- top dimensions: 
- SHA256 image rows: 0
- errors: 6

### prabh-decoders-braillevision__dataset__braille_merged

- data.yaml: `prabh-decoders-braillevision/dataset/braille_merged/data.yaml`
- root: `prabh-decoders-braillevision/dataset/braille_merged`
- images: 1614
- labels: 1614
- annotation rows: 90469
- valid 5-column bounding boxes: 90385
- split images: train=1372, val=242, test=0
- split labels: train=1372, val=242, test=0
- split annotations: train=77597, val=12872, test=0
- split boxes: train=77513, val=12872, test=0
- classes: `{"0": "a", "1": "b", "2": "c", "3": "d", "4": "e", "5": "f", "6": "g", "7": "h", "8": "i", "9": "j", "10": "k", "11": "l", "12": "m", "13": "n", "14": "o", "15": "p", "16": "q", "17": "r", "18": "s", "19": "t", "20": "u", "21": "v", "22": "w", "23": "x", "24": "y", "25": "z"}`
- class IDs seen: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- top dimensions: 640x640=1324, 1024x1376=242, 1024x1536=23, 1024x1024=10, 1024x768=5, 1024x1824=4, 1024x2240=2, 1024x1408=1
- SHA256 image rows: 1614
- errors: 84

### sangam-Braillie__dataset

- data.yaml: `sangam-Braillie/dataset/data.yaml`
- root: `sangam-Braillie/dataset`
- images: 2062
- labels: 2062
- annotation rows: 36429
- valid 5-column bounding boxes: 35755
- split images: train=1757, val=206, test=99
- split labels: train=1757, val=206, test=99
- split annotations: train=31948, val=2954, test=1527
- split boxes: train=31316, val=2937, test=1502
- classes: `{"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F", "6": "G", "7": "H", "8": "I", "9": "J", "10": "K", "11": "L", "12": "M", "13": "N", "14": "O", "15": "P", "16": "Q", "17": "R", "18": "S", "19": "T", "20": "U", "21": "V", "22": "W", "23": "X", "24": "Y", "25": "Z"}`
- class IDs seen: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- top dimensions: 640x640=2062
- SHA256 image rows: 2062
- errors: 674

## Models Found

- `asmitha/runs/detect/braille_detector/weights/best.pt` (24518499 bytes)
- `asmitha/runs/detect/braille_detector/weights/last.pt` (24518499 bytes)
- `asmitha/runs/detect/braille_detector-3/weights/best.pt` (6222634 bytes)
- `asmitha/runs/detect/braille_detector-3/weights/last.pt` (6222634 bytes)
- `asmitha/runs/detect/braille_detector-4/weights/best.pt` (6265642 bytes)
- `asmitha/runs/detect/braille_detector-4/weights/last.pt` (6265642 bytes)
- `asmitha/yolov8n.pt` (6549796 bytes)
- `braille_hackathon_siddhant/model/best.pt` (52052102 bytes)
- `prabh-decoders-braillevision/model/best.pt` (52052178 bytes)
- `prabh-decoders-braillevision/model/best_A.pt` (52052178 bytes)
- `prabh-decoders-braillevision/model/best_B.pt` (22537258 bytes)
- `prabh-decoders-braillevision/model/best_C.pt` (5477338 bytes)
- `sangam-Braillie/model/best.onnx` (104396132 bytes)
- `sangam-Braillie/model/best.pt` (52057810 bytes)
- `sangam-Braillie/model/yolov8_braille.pt` (52095968 bytes)
- `sciobraille-scanner/android/app/build/intermediates/assets/debug/mergeDebugAssets/best_int8.tflite` (26381430 bytes)
- `sciobraille-scanner/android/app/build/intermediates/assets/release/mergeReleaseAssets/best_int8.tflite` (26381430 bytes)
- `sciobraille-scanner/android/app/build/intermediates/bundle_dependency_report/release/configureReleaseDependencies/dependencies.pb` (7076 bytes)
- `sciobraille-scanner/android/app/build/intermediates/metadata_library_dependencies_report/release/collectReleaseDependencies/dependencies.pb` (7076 bytes)
- `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite` (26381430 bytes)
- `sciobraille-scanner/backend/model/best.onnx` (103766655 bytes)
- `sciobraille-scanner/backend/model/best.pt` (22537258 bytes)
- `sciobraille-scanner/backend/model/best_previous_A.pt` (52052178 bytes)
- `sciobraille-scanner/backend/model/best_previous_B.pt` (22537258 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/best_float16.tflite` (51900502 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/best_float32.tflite` (103691374 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/best_full_integer_quant.tflite` (26446798 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/best_int8.tflite` (26381430 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/best_integer_quant.tflite` (26447062 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/fingerprint.pb` (76 bytes)
- `sciobraille-scanner/backend/model/best_saved_model/saved_model.pb` (103892767 bytes)

## Training Scripts Found

- `asmitha/train.py`
- `braille_hackathon_siddhant/training/train.py`
- `prabh-decoders-braillevision/converters/angelina_to_yolo.py`
- `prabh-decoders-braillevision/training/train_kaggle.py`
- `prabh-decoders-braillevision/training/train_kaggle_v11.py`
- `sangam-Braillie/training/train.py`

## Inference Scripts Found

- `asmitha/app.py`
- `asmitha/inference.py`
- `braille_hackathon_siddhant/backend/app.py`
- `braille_hackathon_siddhant/backend/inference.py`
- `braille_hackathon_siddhant/backend/inference_cli.py`
- `braille_hackathon_siddhant/tests/test_api.py`
- `prabh-decoders-braillevision/api_server.py`
- `prabh-decoders-braillevision/app.py`
- `prabh-decoders-braillevision/app_web.py`
- `prabh-decoders-braillevision/final_live_app.py`
- `prabh-decoders-braillevision/inference.py`
- `sangam-Braillie/app.py`
- `sangam-Braillie/inference/predict.py`
- `sangam-Braillie/main.py`
- `sciobraille-scanner/backend/inference.py`
- `sciobraille-scanner/backend/lms_api.py`
- `sciobraille-scanner/backend/scanner_api.py`
- `sciobraille-scanner/backend/tests/test_scanner_preprocessing.py`

## Benchmark / Evaluation Assets Found

- `asmitha/sample_inputs/1067_jpg.rf.be50e49c6bf357ba8cb664cac7ffd9b9.jpg`
- `asmitha/sample_inputs/1070_jpg.rf.a407a00781392ecf7ce10a35a9e0adf3.jpg`
- `asmitha/sample_inputs/1071_jpg.rf.316e5472056d74bf08538aac50ea4d22.jpg`
- `asmitha/sample_inputs/1080_jpg.rf.95aa3358d3f09e244e0314962d3fc34b.jpg`
- `asmitha/sample_inputs/1097_jpg.rf.6774c7b6f4e66bb1adcc86273677b34e.jpg`
- `asmitha/sample_outputs/Screenshot 2026-06-01 at 11.47.57 AM.png`
- `asmitha/sample_outputs/Screenshot 2026-06-01 at 11.48.05 AM.png`
- `asmitha/sample_outputs/Screenshot 2026-06-01 at 11.48.34 AM.png`
- `asmitha/sample_outputs/Screenshot 2026-06-01 at 11.48.42 AM.png`
- `asmitha/sample_outputs/Screenshot 2026-06-01 at 11.57.07 AM.png`
- `braille_hackathon_siddhant/demo/demo_video_link.txt`
- `braille_hackathon_siddhant/demo/FINAL_VIDEO_SCRIPT.txt`
- `prabh-decoders-braillevision/demo/demo_video_link.txt`
- `prabh-decoders-braillevision/sample_inputs/braille_book_page.jpg`
- `prabh-decoders-braillevision/sample_inputs/braille_camera_capture.jpg`
- `prabh-decoders-braillevision/sample_inputs/braille_handwritten.jpg`
- `prabh-decoders-braillevision/sample_inputs/judge_test.png`
- `prabh-decoders-braillevision/sample_inputs/judge_test_clahe.png`
- `prabh-decoders-braillevision/sample_inputs/README.txt`
- `prabh-decoders-braillevision/sample_outputs/braille_book_page_out.jpg`
- `prabh-decoders-braillevision/sample_outputs/braille_book_page_out.txt`
- `prabh-decoders-braillevision/sample_outputs/braille_camera_capture_out.jpg`
- `prabh-decoders-braillevision/sample_outputs/braille_camera_capture_out.txt`
- `prabh-decoders-braillevision/sample_outputs/braille_handwritten_out.jpg`
- `prabh-decoders-braillevision/sample_outputs/braille_handwritten_out.txt`
- `prabh-decoders-braillevision/sample_outputs/judge_test_clahe_out.jpg`
- `prabh-decoders-braillevision/sample_outputs/judge_test_clahe_out.txt`
- `prabh-decoders-braillevision/sample_outputs/judge_test_out.jpg`
- `prabh-decoders-braillevision/sample_outputs/judge_test_out.txt`
- `prabh-decoders-braillevision/sample_outputs_compare_mohan/judge_test_out.jpg`
- `prabh-decoders-braillevision/sample_outputs_compare_mohan/judge_test_out.txt`
- `sangam-Braillie/sample_input/12_jpg.rf.20353e71697f42d6426d0a25ce58bc10.jpg`
- `sangam-Braillie/sample_input/17_jpg.rf.f3f269294d079b41dcadb0cd41465b61.jpg`
- `sangam-Braillie/sample_input/3_jpg.rf.ebd8a994d7bb7fbcc98b8600ff936036.jpg`
- `sangam-Braillie/sample_input/6_jpg.rf.82e84c41ec33b4140121aabfa4be36c5.jpg`
- `sangam-Braillie/sample_outputs_fast/12_jpg.rf.20353e71697f42d6426d0a25ce58bc10_result.jpg`
- `sangam-Braillie/sample_outputs_fast/17_jpg.rf.f3f269294d079b41dcadb0cd41465b61_result.jpg`
- `sangam-Braillie/sample_outputs_fast/3_jpg.rf.ebd8a994d7bb7fbcc98b8600ff936036_result.jpg`
- `sangam-Braillie/sample_outputs_fast/6_jpg.rf.82e84c41ec33b4140121aabfa4be36c5_result.jpg`
- `sangam-Braillie/sample_outputs_judge/judge_test_result.png`
- `sangam-Braillie/sample_outputs_judge_onnx/judge_test_result.png`
- `sangam-Braillie/sample_outputs_test/12_jpg.rf.20353e71697f42d6426d0a25ce58bc10_result.jpg`
- `sangam-Braillie/sample_outputs_test/17_jpg.rf.f3f269294d079b41dcadb0cd41465b61_result.jpg`
- `sangam-Braillie/sample_outputs_test/3_jpg.rf.ebd8a994d7bb7fbcc98b8600ff936036_result.jpg`
- `sangam-Braillie/sample_outputs_test/6_jpg.rf.82e84c41ec33b4140121aabfa4be36c5_result.jpg`
- `sciobraille-scanner/android/app/build/intermediates/annotation_processor_list/debugUnitTest/javaPreCompileDebugUnitTest/annotationProcessors.json`
- `sciobraille-scanner/android/app/build/intermediates/bundle_ide_model/release/produceReleaseBundleIdeListingFile/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/compatible_screen_manifest/debug/createDebugCompatibleScreenManifests/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/compatible_screen_manifest/release/createReleaseCompatibleScreenManifests/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/linked_resources_binary_format/debug/processDebugResources/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/linked_resources_binary_format/release/processReleaseResources/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/merged_manifests/debug/processDebugManifest/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/merged_manifests/release/processReleaseManifest/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/packaged_manifests/debug/processDebugManifestForPackage/output-metadata.json`
- `sciobraille-scanner/android/app/build/intermediates/packaged_manifests/release/processReleaseManifestForPackage/output-metadata.json`
- `sciobraille-scanner/android/app/build/outputs/apk/debug/output-metadata.json`
- `sciobraille-scanner/android/app/build/outputs/logs/manifest-merger-debug-report.txt`
- `sciobraille-scanner/android/app/build/outputs/logs/manifest-merger-release-report.txt`
- `sciobraille-scanner/android/app/build/outputs/mapping/release/configuration.txt`
- `sciobraille-scanner/android/app/build/outputs/mapping/release/mapping.txt`
- `sciobraille-scanner/android/app/build/outputs/mapping/release/seeds.txt`
- `sciobraille-scanner/android/app/build/outputs/mapping/release/usage.txt`

## Model To Dataset Mapping, Evidence-Based

- `sciobraille-scanner/backend/model/best.pt`: documented as Prabh Model B, trained from `prabh-decoders-braillevision/dataset/braille_merged`.
- `sciobraille-scanner/backend/model/best_previous_A.pt`: duplicate lineage of Prabh Model A.
- `prabh-decoders-braillevision/model/best.pt`: documented Model A/large benchmark from Prabh project.
- `prabh-decoders-braillevision/model/best_B.pt`: same active production model lineage.
- `sangam-Braillie/model/best.pt`: Sangam 26-class model, expected to use `sangam-Braillie/dataset`.
- `sangam-Braillie/model/yolov8_braille.pt`: 64-class dot-pattern model; dataset linkage needs manual validation.
- `asmitha/runs/detect/*/weights/*.pt`: Asmitha training runs, expected to use `asmitha/dataset`.
- `braille_hackathon_siddhant/model/best.pt`: Siddhant reference model; included dataset appears incomplete locally.

## Problems Discovered

- invalid_label_columns: 842
- missing_split_images_dir: 3
- missing_split_labels_dir: 3

Detailed rows: `dataset_errors.csv`.
