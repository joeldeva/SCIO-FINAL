# BRAILLEVISION File Inventory Explained

This report explains the cleaned BRAILLEVISION folder after dataset consolidation. The exact per-file inventory is in `file_inventory_explained.csv`.

## Counts

| Category | File count |
|---|---|
| Master V2 dataset image | 1784 |
| Master V2 YOLO label | 1784 |
| Report/evaluation output | 100 |
| Reference project - Prabh | 92 |
| Reference project - Asmitha | 75 |
| Production Android app | 73 |
| Model artifact | 54 |
| Reference project - Sangam | 38 |
| Archived experiment | 38 |
| Reference project - Siddhant | 36 |
| Exported model | 26 |
| Production backend | 17 |
| Model-lab script | 15 |
| Product documentation | 18 |
| Benchmark asset | 11 |
| Master V2 dataset metadata | 5 |
| Manual test image | 4 |
| Training/inference config | 3 |
| Release artifact | 3 |
| Training script | 2 |
| Production helper script | 1 |
| Base model checkpoint | 1 |

## Important folders

- `sciobraille-scanner/`: active production prototype. Contains Android app, FastAPI backend, production model, TFLite model, release APKs, tests, and product docs.
- `sciobraille-model-lab/`: reproducible model lab. Contains the canonical Master V2 dataset, V1/V2 models, exports, benchmark images, scripts, configs, reports, and archived experiments.
- `asmitha/`, `prabh-decoders-braillevision/`, `sangam-Braillie/`, `braille_hackathon_siddhant/`: retained reference projects. Their original datasets were removed; useful code/docs/models/sample outputs remain for reference.

## Dataset rule

The only active training dataset is `sciobraille-model-lab/datasets/master_v2/`. Image files under `images/train`, `images/val`, and `images/test` are the canonical unique Braille images. Label files under `labels/train`, `labels/val`, and `labels/test` are YOLO annotations paired by filename stem.

## Production runtime rule

The app and backend runtime live under `sciobraille-scanner/`. The backend production PyTorch model is `sciobraille-scanner/backend/model/best.pt`; Android offline runtime uses `sciobraille-scanner/android/app/src/main/assets/best_int8.tflite`.

## How to read the CSV

Each row gives: `path`, `category`, `purpose`, and `keep`. Dataset images/labels are grouped by purpose because each individual image/label serves the same dataset role.
