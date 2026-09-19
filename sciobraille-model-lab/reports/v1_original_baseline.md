# Sciobraille V1 Original Baseline

Read-only baseline. No training. Production model not modified.

## Model

- path: `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\sciobraille-scanner\backend\model\best.pt`
- size bytes: `22537258`
- size MB: `21.4932`

## Detection Metrics

- data: `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\prabh-decoders-braillevision\dataset\braille_merged\data.yaml`
- split: `val`
- precision: `0.9571808063090196`
- recall: `0.9085072169253933`
- mAP50: `0.952241253269704`
- mAP50-95: `0.775037211935685`
- note: Detection metrics use YOLO validation data, not independent physical text benchmark.

## Text Metrics

Text accuracy uses `raw_text` only. `corrected_text` saved for comparison, not scoring.

- samples: `3`
- Character Error Rate: `0.40103463787674315`
- Word Error Rate: `0.6547619047619048`
- character accuracy: `0.5989653621232568`
- word accuracy: `0.3452380952380952`
- exact sentence accuracy: `0.0`
- average inference latency ms: `304.34315554965804`
- median inference latency ms: `321.7176999896765`

## Benchmark Caveat

Independent physical benchmark is still too small. Add 50-100 held-out phone-camera physical Braille images with exact human ground truth before using text metrics as release gate.

## Files

- predictions: `reports/v1_original_predictions.csv`
- JSON: `reports/v1_original_baseline.json`