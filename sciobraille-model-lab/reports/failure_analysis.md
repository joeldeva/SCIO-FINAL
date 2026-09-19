# Sciobraille Failure Analysis Gate

## Status

Requested condition-level failure analysis cannot be calculated honestly from the current frozen benchmark.
The benchmark has only three images, two of which show the same DMI content in original and flipped form.

## Current Raw-Text Failures

Existing controlled Model B/V1 evidence:

| Sample | Raw CER | Raw WER | Main failure |
|---|---:|---:|---|
| `scio_known_01` | 0.017544 | 0.142857 | Missed initial `v` in `visually` |
| `dmi_root_01` | 1.000000 | 1.000000 | No detections on unflipped reverse-side image |
| `dmi_flipped_01` | 0.038462 | 0.250000 | Final character missing from `engineering` |

Model B and V1 have the same SHA256, so their failure behavior is identical.
No V2 failure evidence exists.

## Requested Category Coverage

| Category | Frozen samples with explicit label | Analysis status |
|---|---:|---|
| Normal lighting | 0 | Missing metadata |
| Dim lighting | 0 | Missing samples and metadata |
| Harsh lighting | 0 | Missing samples and metadata |
| Shadows | 0 | Missing samples and metadata |
| Blur | 0 | Missing samples and metadata |
| Perspective | 0 | Missing samples and metadata |
| Close range | 0 | Missing samples and metadata |
| Long range | 0 | Missing samples and metadata |
| Reverse-side Braille | 2 related DMI images | Model requires correct horizontal orientation; unflipped input failed completely |
| Multiple lines | 3 images | Present, but too few independent documents for a reliable rate |
| Word spacing | 3 images | Present, but no spacing-difficulty label or enough independent documents |

## Benchmark Schema Needed

Add these frozen columns to each independent sample:

`lighting`, `shadow_level`, `blur_level`, `perspective_level`, `range`, `braille_side`, `line_count`, `spacing_difficulty`, `document_group`, and `capture_group`.

For detection metrics, add one YOLO label file per benchmark image. Keep all benchmark images and derived captures outside every training dataset.

Do not use corrected text, fuzzy matching, hardcoded vocabulary, or spell correction for failure scoring.
