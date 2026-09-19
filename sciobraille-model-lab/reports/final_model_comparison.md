# Sciobraille Final Model Comparison Gate

## Status

Final three-model comparison is **blocked**. No V2 Master checkpoint exists under `models/v2_master/`.
The report does not invent V2 metrics or declare a winner.

## Artifact Check

| Model | Status | SHA256 | Size |
|---|---|---|---:|
| Original production Model B | Available | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` | 22,537,258 bytes |
| V1 Optimized | Available, byte-identical to Model B | `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974` | 22,537,258 bytes |
| V2 Master winner | Missing | Not available | Not available |

V1 training did not beat Model B on raw CER. The controlled V1 selection therefore copied Model B unchanged.
Model B and V1 are one model artifact, not two distinct candidates.

## Available Provisional Evidence

These values come from the existing V1 controlled evaluation. Text accuracy uses `raw_text` only.
Spell correction and `corrected_text` do not affect any score.

| Model | Raw CER | Raw WER | Character accuracy | Word accuracy | Sentence exact match | Precision | Recall | mAP50 | mAP50-95 | Average latency | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Model B | 0.352002 | 0.464286 | 0.647998 | 0.535714 | 0.000000 | 0.957181 | 0.908628 | 0.945167 | 0.750643 | 230.12 ms | 190.66 ms |
| V1 Optimized | 0.352002 | 0.464286 | 0.647998 | 0.535714 | 0.000000 | 0.957181 | 0.908628 | 0.945167 | 0.750643 | 230.12 ms | 190.66 ms |
| V2 Master | Not available | Not available | Not available | Not available | Not available | Not available | Not available | Not available | Not available | Not available | Not available |

Detection metrics above are retained only as provisional evidence. They were measured on the Prabh validation set.
That set is not a valid common final detection benchmark for a future V2 trained from Master V2 because source overlap can cause leakage.

## Frozen Benchmark Audit

`benchmark/ground_truth.csv` contains three physical images representing two Braille documents:

- `scio_known_01`
- `dmi_root_01`
- `dmi_flipped_01`

The benchmark has text ground truth but no bounding-box annotations. Therefore it can calculate raw CER/WER and latency, but not precision, recall, mAP50, or mAP50-95.
It also lacks structured condition labels for most requested failure categories.

## Required Before Final Selection

1. Train V2 candidates from `datasets/master_v2/data.yaml` and select a V2 winner without touching production.
2. Keep `models/v2_master/best.pt`, its configuration, SHA256, and evaluation record.
3. Create an independent, leakage-safe detection benchmark with YOLO bounding-box labels.
4. Expand the physical text benchmark to at least 50-100 independently captured images.
5. Add explicit condition fields for lighting, shadows, blur, perspective, range, side, line count, and spacing.
6. Freeze benchmark hashes, then run all distinct model artifacts with one inference configuration and environment.

Production model remains unchanged. No model was deleted.
