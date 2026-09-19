# Sciobraille V1 Optimized

## Status

Active release candidate retained by the controlled V1 selection process.

The fine-tuned checkpoints did not improve raw Character Error Rate on the frozen physical benchmark. The selected V1 artifact is therefore byte-identical to the original production Model B.

## Files

- `best.pt`: selected model checkpoint
- `config.yaml`: training, dataset, environment, and selection configuration
- `evaluation.json`: raw-text benchmark results and candidate comparison
- `README.md`: model card

## Identity

- SHA256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- Size: `22,537,258` bytes
- Classes: `a` through `z`
- Architecture: YOLO Braille-cell detector
- Training lineage: Prabh merged Braille dataset

## Selected Metrics

- Raw CER: `0.35200179937022047`
- Raw WER: `0.46428571428571425`
- Character accuracy: `0.6479982006297796`
- Word accuracy: `0.5357142857142857`
- Precision: `0.9571812844286474`
- Recall: `0.9086278246795114`
- mAP50: `0.9451669352836093`
- mAP50-95: `0.7506425713897258`
- Average latency: `230.12472222196973 ms`
- Median latency: `190.65890001365915 ms`

Text accuracy uses raw recognition output. Corrected text does not affect model selection.
