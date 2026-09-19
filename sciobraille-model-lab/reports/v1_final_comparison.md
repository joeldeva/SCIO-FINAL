# Sciobraille V1 Final Comparison

V1 uses the production checkpoint and its original Prabh merged dataset lineage only.
Text accuracy uses raw text. Corrected text never affects selection.

## Selected Candidate

- source: `C:\Users\devaj\OneDrive\Documents\BRAILLEVISION\sciobraille-scanner\backend\model\best.pt`
- SHA256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- raw CER: `0.35200179937022047`
- raw WER: `0.46428571428571425`
- recall: `0.9086278246795114`
- mAP50: `0.9451669352836093`
- mAP50-95: `0.7506425713897258`
- average latency ms: `230.12472222196973`

## Candidate Comparison

| Candidate | Raw CER | Raw WER | Recall | mAP50-95 | Latency ms |
|---|---:|---:|---:|---:|---:|
| `best.pt` `b9269091` | 0.352002 | 0.464286 | 0.908628 | 0.750643 | 230.12 |
| `epoch0.pt` `db964eee` | 0.364822 | 0.464286 | 0.919276 | 0.754056 | 166.30 |
| `epoch5.pt` `5f7f698a` | 0.370670 | 0.511905 | 0.920854 | 0.759577 | 176.24 |
| `last.pt` `3f04390c` | 0.370670 | 0.511905 | 0.919923 | 0.759782 | 163.26 |
| `epoch25.pt` `150a3b2e` | 0.370670 | 0.511905 | 0.919923 | 0.759782 | 164.36 |
| `best.pt` `06e5b886` | 0.370670 | 0.511905 | 0.918119 | 0.763814 | 171.67 |
| `epoch10.pt` `0ef94f1b` | 0.376518 | 0.559524 | 0.912612 | 0.756594 | 164.65 |
| `epoch15.pt` `06fae94f` | 0.383491 | 0.595238 | 0.919988 | 0.757956 | 159.64 |
| `epoch20.pt` `0c7f1288` | 0.383491 | 0.595238 | 0.916853 | 0.757326 | 161.64 |

## Reproducibility

- initialization SHA256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- dataset fingerprint: `5d93de13cd16438a660b3eb015e7012f0d241aab1cee3360a579c95cbdc81454`
- dataset images: `1614`
- dataset labels: `1614`
- seed: `20260917`
- epochs completed: `26` of `30`
- early stopping: `True`
- training best mAP50-95: `0.75682` at epoch `19`
- Python: `3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]`
- PyTorch: `2.8.0+cu128`
- Ultralytics: `8.4.14`
- CUDA available: `True`

## Safety

- production SHA256 after completion: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`
- production model overwritten: `false`
- V2 merged dataset used: `false`