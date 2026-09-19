# Sciobraille Master Dataset V2

Canonical 26-class English Grade 1 Braille-cell detection dataset.

## Counts

- candidate images: 5001
- valid candidates before deduplication: 5001
- retained unique images: 826
- bounding boxes: 75653
- train/val/test: 660/79/87

## Construction

Sources: Prabh merged, Sangam Braillie, and Asmitha. No source file was changed or deleted.
Mappings were normalized to `0=a` through `25=z`. Valid polygon rows were explicitly converted to boxes.
Images with unsupported classes or invalid annotations were excluded and reported.
SHA256, perceptual hash, dHash, normalized capture names, and conservative near-duplicate matching formed leakage groups.
One representative was retained per group. External physical benchmark images remain separate.

See `provenance.csv`, `dataset_statistics.json`, and reports under `sciobraille-model-lab/reports/`.
