# Archived Model Experiments

This directory stores reversible archives of non-selected model experiments. No source dataset, source-project model, production model, or historical checkpoint was deleted.

Large checkpoints were moved on the same filesystem instead of copied. `model_manifest.csv` records checkpoint identity, origin, dataset lineage, available metrics, and archive reason.

## V1 Archive

- `v1_optimized/runs/`: interrupted and completed training runs
- `v1_optimized/validation/`: candidate validation outputs
- `v1_optimized/control_files/`: logs and process-control records

Paths recorded in historical evaluation files may refer to their original pre-archive locations. Use `model_manifest.csv` to resolve archived checkpoint locations.
