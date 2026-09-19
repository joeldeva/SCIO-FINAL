# Sciobraille Benchmark

Purpose: reproducible baseline for existing production model:

`sciobraille-scanner/backend/model/best.pt`

Rules:

- Score text accuracy from `raw_text` only.
- Do not score `corrected_text`.
- Do not use spell correction, demo vocabulary, hardcoded corrections, fuzzy matching, or language correction for benchmark accuracy.
- Do not train.
- Do not overwrite production model.

## Ground Truth

`ground_truth.csv` has known physical Braille samples with exact expected English text.

Current benchmark is intentionally small. It is not enough for release-grade model selection.

Need next:

- 50-100 independent phone-camera physical Braille images.
- Human-verified English transcription.
- Multiple lighting conditions.
- Front-side and reverse-side Braille.
- Different paper textures.
- Different distances and tilt.
- Separate benchmark images from all training data.

## Run

```powershell
python sciobraille-model-lab\scripts\benchmark_model.py
```

Outputs:

- `sciobraille-model-lab/reports/v1_original_baseline.md`
- `sciobraille-model-lab/reports/v1_original_baseline.json`
- `sciobraille-model-lab/reports/v1_original_predictions.csv`
