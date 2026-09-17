# Model & Dataset Information

## Model Used
- **Base Model:** YOLOv8m (Foundation Model via DotNeuralNet)
- **Fine-Tuning:** Fine-tuned to map directly to 26 A-Z English classes
- **Format:** PyTorch `.pt`
- **File:** `model/best.pt`
- **Task:** Object Detection — Braille character classification
- **Classes:** 26 (a-z)
- **Final Metrics:** mAP50 of 0.931 on the validation set
- **Training Hardware:** Local NVIDIA T4 Tensor Core GPU (Google Colab)

> The YOLOv8n base model was fine-tuned on the Kaggle Braille Character Dataset. On top of the model we built a custom full-stack application layer: HTTP-based inference pipeline, multi-pass heuristic text repair, TTS audio output, and a dual-accessibility UI with voice commands.

## Dataset Information
- **Primary Datasets:** 
  1. DSBI (Double-Sided Braille Image) Dataset
  2. Kaggle Braille Alphabet (26-Class) Dataset
  3. Custom Hand-Curated Physical Paper Images
- **Total Volume:** ~1,614 images
- **Annotation Format:** YOLO format (`.txt` files with normalized bounding box coordinates)
- **Class Names:** a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z (26 classes)
- **Dataset Download:** The open-source DSBI and Kaggle datasets can be downloaded directly from their respective public endpoints. The custom physical paper subset is provided in `sample_dataset.zip` for local testing.

## Train / Validation / Test Split
- **Train:** ~1,350 images (75%)
- **Validation:** ~270 images (15%)
- **Test:** ~180 images (10%)
- **Split Method:** Random stratified split

Note: Only a representative subset of the training data is included directly in the repository (`dataset/images/train/` and `dataset/images/val/`).

## Preprocessing Steps
1. **Resize:** All images resized to 640x640 (YOLO default input size)
2. **Morphological Top-Hat:** Elliptical kernel (3x3) applied to enhance dot contrast against paper background
3. **CLAHE:** Contrast Limited Adaptive Histogram Equalization (clipLimit=3.0, tileGridSize=8x8) to normalize uneven lighting across the image
4. **Adaptive Thresholding:** Gaussian adaptive threshold (blockSize=15, C=2) to binarize dot regions
5. **Inversion:** Binary inversion so Braille dots appear as white on black background
6. **Multi-variant inference:** At runtime, three image variants are generated (original, high-contrast CLAHE, darkened gamma=2.0) and the best result is selected

## Key Training Decisions
- **fliplr=0.0, flipud=0.0:** Flip augmentations were explicitly disabled because Braille is chiral — mirroring a character changes its meaning (e.g., 'r' becomes 'w')
- **Batch Size:** 8 (optimized for Colab T4 memory constraints)
- **cache=False:** Disabled dataset caching to prevent RAM exhaustion on free-tier Colab

## Training Reproduction
The training scripts (`training/train.py` and `training/braille_train.ipynb`) contain the training logic used during the Colab session. The `best.pt` checkpoint is the output of this combined training process and is provided directly in the repository.
