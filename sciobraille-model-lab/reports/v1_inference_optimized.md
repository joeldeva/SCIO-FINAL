# Sciobraille V1 Inference Optimization

Inference-only staged search. Production model and scanner code were not modified. No training performed.

## Selection Rule

Primary objective: lowest mean of raw CER and raw WER. Latency breaks close ties. Corrected text never affects scoring.
Ground-truth-dependent `benchmark_metadata` flipping is excluded from final selection.

## Best Configuration

- confidence: `0.5`
- iou: `0.5`
- preprocessing: `current_production`
- tta: `True`
- line_clustering: `adaptive`
- line_tolerance: `0.6`
- spacing_multiplier: `1.8`
- width_multiplier: `1.35`
- duplicate_handling: `class_agnostic`
- duplicate_iou: `0.7`
- flip_strategy: `never`
- imgsz: `640`

## Result

- raw CER: `0.35200179937022047` (original `0.40103463787674315`)
- raw WER: `0.46428571428571425` (original `0.6547619047619048`)
- character accuracy: `0.6479982006297796`
- word accuracy: `0.5357142857142857`
- exact sentence accuracy: `0.0`
- average latency ms: `1445.4313666663236` (original `304.34315554965804`)
- median latency ms: `1243.948299990734` (original `321.7176999896765`)
- precision: `0.9582460504712151`
- recall: `0.9200539211777716`
- mAP50: `0.9577679623713978`
- mAP50-95: `0.6959098085990152`

## Search

- configurations evaluated: `46`
- stages: confidence, IoU, preprocessing/TTA, reconstruction, combined finalists
- confidence values: `0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50`
- IoU values: `0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60`
- preprocessing: `raw, current_production, bilateral, clahe, clahe_bilateral, illumination_normalization`
- full results: `reports/v1_inference_search.csv`

## Limits

Only `3` independent physical benchmark images exist. Configuration is provisional and likely overfit.
Add 50-100 held-out physical phone-camera images before release gating or production adoption.
Detection metrics use merged-dataset validation images, not independent physical images.

## Integrity

- production model SHA256 before and after search: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- production model overwritten: `false`
- production scanner modified: `false`
- training performed: `false`