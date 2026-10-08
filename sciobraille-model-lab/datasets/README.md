# Sciobraille Dataset

This directory contains the single canonical dataset used by the active Sciobraille V2 model:

- `master_v2/`: 1,784 unique images and 99,352 YOLO bounding boxes.
- Splits: 1,440 train, 165 validation, and 179 internal test images.
- Classes: 26 English Grade 1 Braille letters, `0=a` through `25=z`.

Master V2 consolidates useful unique samples from the Prabh, Sangam, and Asmitha source datasets. The redundant source dataset copies were removed from the current repository after consolidation. Their origins, hashes, original splits, mappings, and paths remain recorded in `master_v2/provenance.csv` and `master_v2/dataset_statistics.json`.

The external physical benchmark is intentionally separate under `sciobraille-model-lab/benchmark/` and must not be used for training.
