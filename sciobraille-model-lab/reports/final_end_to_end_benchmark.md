# Final End-to-End Braille Benchmark

Accuracy source: `raw_text` only. Corrected text did not affect any metric.

The frozen benchmark contains three physical phone-camera samples. Results are regression evidence, not a production accuracy claim.

| Runtime | CER | WER | Character accuracy | Word accuracy | Exact match | Average latency | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Backend PT | 0.3520 | 0.4643 | 0.6480 | 0.5357 | 0.0000 | 270.94 ms | 188.64 ms |
| Android INT8 artifact | 0.3520 | 0.4643 | 0.6480 | 0.5357 | 0.0000 | 581.40 ms | 490.38 ms |

## Failure Breakdown

### scio_known_01

- Backend raw CER/WER: 0.0175 / 0.1429
- Offline raw CER/WER: 0.0175 / 0.1429
- Backend detections: 50
- Offline detections: 50
- Backend raw: `jaihind / india / sciobraille / isually impaired / great project`
- Offline raw: `jaihind / india / sciobraille / isually impaired / great project`

### dmi_root_01

- Backend raw CER/WER: 1.0000 / 1.0000
- Offline raw CER/WER: 1.0000 / 1.0000
- Backend detections: 0
- Offline detections: 0
- Backend raw: `<empty>`
- Offline raw: `<empty>`

### dmi_flipped_01

- Backend raw CER/WER: 0.0385 / 0.2500
- Offline raw CER/WER: 0.0385 / 0.2500
- Backend detections: 22
- Offline detections: 22
- Backend raw: `dmi college / of engineerin`
- Offline raw: `dmi college / of engineerin`

## Observed Failures

- Both runtimes fail on the DMI source orientation when default horizontal flipping is applied. They read the already-flipped copy when flipping is disabled. Automatic orientation selection is not implemented.
- Both runtimes miss the initial `v` in `visually` and the final `g` in `engineering` in raw output.
- Backend and offline raw recognition match on all three samples. Windows TFLite latency is not representative of phone latency.
- Exact sentence match is zero for both runtimes.
- Lighting, blur, distance, perspective, and spacing categories cannot be measured independently because the frozen set lacks enough labeled samples.

## Required Benchmark Expansion

Add 50-100 independent physical samples with exact ground truth and category labels for normal/dim/harsh light, shadows, blur, perspective, close/long range, reverse-side Braille, multiple lines, and word spacing.
