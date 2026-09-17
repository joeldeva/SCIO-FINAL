# Dataset Information

## Merged Dataset: braille_merged

| Metric | Value |
|--------|-------|
| Total images | 1,614 |
| Total bounding boxes | 90,469 |
| Classes | 26 (a–z) |
| Train split | 1,372 images (85%) |
| Val split | 242 images (15%) |
| Image format | YOLO (images/ + labels/ with .txt) |

## Sources

### 1. yapayzeka/braille-detection-vxtp1 (Roboflow)
- **Images**: 1,324
- **Boxes**: ~21,000
- **Type**: Mixed braille images (embossed, camera-captured)
- **Download**: Via Roboflow API
- **License**: Roboflow Universe (public)

### 2. Angelina Braille Images Dataset (GitHub)
- **Images**: 290
- **Boxes**: ~69,000 (dense annotations — many cells per page)
- **Type**: Real book photos (212) + handwritten student work (28) + other (50)
- **Original format**: CSV with bitmask-encoded labels
- **Conversion**: Custom `converters/angelina_to_yolo.py`
- **Source**: https://github.com/IlyaOvodov/AngelinaDataset
- **License**: Research use

## Class Distribution

All 26 English Braille letters (a–z) are represented. Distribution follows natural letter frequency from the source texts, with common letters (e, a, o, n, s) having more samples.

## Preprocessing

- All class names normalized to lowercase a–z
- Images deduplicated by MD5 content hash
- Deterministic 85/15 train/val split (random seed = 42)
- Angelina bitmask integers decoded to dot patterns, then mapped to Braille letters

## Merge Pipeline

Run `merge_datasets.py` to reproduce the merge. The script:
1. Reads from configured source directories
2. Detects directory layout (Roboflow vs standard YOLO vs flat)
3. Normalizes class names across sources
4. Removes duplicate images (by content hash)
5. Splits into train/val
6. Generates `data.yaml` for Ultralytics training
