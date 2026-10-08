# Sciobraille Independent Field Testing Instructions

**Document Version:** 1.0.0
**Target:** Real-world Physical Braille Validation Protocol for V1 vs V2
**Script Runner:** `sciobraille-model-lab/scripts/evaluate_field_samples.py`
**Manifest Schema:** `sciobraille-model-lab/benchmark/independent_physical_schema.py`

---

## 1. Objective & Principles

The 3-image physical benchmark is insufficient to select a production winner because 1 image was captured upside down (yielding zero detections for both models) and the remaining 2 images cannot provide statistical significance.

This document establishes the official protocol for evaluating **50 to 100 new real-world physical Braille photographs** captured by users or field testers.

### Core Principles
1. **Zero Data Leakage:** All new physical test photographs must be kept in a dedicated directory outside of `datasets/master_v2/`. They must NEVER be used for training, hyperparameter tuning, or prompt calibration.
2. **Ground-Truth Rigor:** Transcriptions must be character-for-character exact Grade 1 Braille.
3. **No Artificial Corrections:** Raw CER and WER must be evaluated directly on the raw text output without spell checkers, dictionary substitutions, or language models.
4. **Side-by-Side Equivalence:** Both models (Production V1 and Master V2) are evaluated on the exact same physical image using identical pipeline parameters.

---

## 2. Recommended Capture Guidelines

To accurately measure model robustness in real-world deployment, collect photographs representing a balanced matrix of physical conditions:

### 2.1 Environmental Conditions Matrix
* **Lighting Variations:**
  - `ambient`: Standard indoor diffuse room lighting.
  - `direct`: Direct overhead light source or smartphone flashlight.
  - `shadow`: Hand, device, or ambient shadows cast across the embossed page.
  - `directional_side_lighting`: Grazing angle illumination creating pronounced dot shadows.
  - `low_light`: Dim evening or underexposed room lighting.
* **Camera Distance & Framing:**
  - `close`: 15–20 cm (macro/cell-level focus).
  - `medium`: 25–40 cm (standard document reading distance).
  - `far`: 45–60 cm (full page capture with smaller cell resolution).
* **Perspective & Tilt:**
  - `planar`: Flat top-down (perpendicular to paper).
  - `slight_tilt`: 10°–25° hand-held angle.
  - `steep_angle`: > 30° perspective distortion.
* **Paper Substrates & Media:**
  - Standard Braille paper (heavy cardstock, 120–160 gsm).
  - Standard copy paper (embossed 80 gsm paper).
  - Embossed plastic or aluminum labeling strips.
  - Double-sided (interpoint) or single-sided embossing.
* **Dot Quality:**
  - Crisp, newly embossed sharp dots.
  - Worn, flattened, or aged Braille dots.

---

## 3. Directory Layout & File Organization

Create a dedicated local directory for field testing:

```text
sciobraille-model-lab/benchmark/independent_physical/
├── images/
│   ├── doc01_ambient_medium.jpg
│   ├── doc01_shadow_tilt.jpg
│   ├── doc02_direct_close.jpg
│   └── ...
├── manifests/
│   └── field_test_round1.csv
└── independent_physical_template.csv
```

> [!WARNING]
> Do NOT store field test images in `sciobraille-model-lab/datasets/master_v2/` or any training folder.

---

## 4. Manifest Format & Metadata Schema

Create a CSV manifest (e.g. `sciobraille-model-lab/benchmark/independent_physical/manifests/field_test_round1.csv`) containing the following columns:

| Column Name | Type | Description | Example |
|---|---|---|---|
| `id` | String | Unique sample identifier | `phys_sample_001` |
| `image_path` | String | Path to photograph (absolute or relative) | `benchmark/independent_physical/images/doc01_ambient_medium.jpg` |
| `ground_truth_transcription` | String | Verbatim raw Braille text (use `\n` for line breaks) | `braille vision\nsmart scanner` |
| `document_id` | String | Identifier for physical source document | `doc_braille_guide_p1` |
| `capture_group_id` | String | Group identifier for multi-shot captures | `group_doc01_desk` |
| `orientation` | String | `front` (raised dots) or `reverse` (indented dots) | `front` |
| `lighting` | String | `ambient`, `direct`, `shadow`, `low_light`, etc. | `ambient` |
| `blur` | String | `sharp`, `mild_motion`, `severe_blur` | `sharp` |
| `distance` | String | `close`, `medium`, `far` | `medium` |
| `perspective` | String | `planar`, `slight_tilt`, `steep_angle` | `planar` |
| `line_count` | Integer | Total number of Braille text lines (>= 1) | `2` |
| `notes` | String | Optional tester remarks | `Heavy cardstock paper` |

### Sample Manifest Entry
```csv
id,image_path,ground_truth_transcription,document_id,capture_group_id,orientation,lighting,blur,distance,perspective,line_count,notes
phys_sample_001,benchmark/independent_physical/images/sample01.jpg,"hello world",doc01,group01,front,ambient,sharp,medium,planar,1,Sample test
```

---

## 5. Execution Workflow

Run the automated field evaluation script from the repository root:

```bash
python sciobraille-model-lab/scripts/evaluate_field_samples.py \
    --manifest sciobraille-model-lab/benchmark/independent_physical/manifests/field_test_round1.csv \
    --output-dir sciobraille-model-lab/reports/field_evaluation \
    --v1-model sciobraille-scanner/backend/model/best.pt \
    --v2-model sciobraille-model-lab/models/v2_master/best.pt \
    --config sciobraille-model-lab/configs/v1_optimized.yaml
```

### Script Execution Steps:
1. **Manifest Validation:** Confirms file existence, column headers, valid orientations (`front`/`reverse`), and non-empty ground-truth strings.
2. **Side-by-Side Inference:** Executes V1 and V2 sequentially using identical preprocessing and text reconstruction rules.
3. **Metric Calculation:** Calculates exact Levenshtein Character Error Rate (CER) and Word Error Rate (WER) per sample.
4. **Report Generation:** Generates:
   - `field_evaluation_report.md` (Markdown summary table with aggregate CER, WER, and per-condition slices).
   - `field_evaluation_comparison.csv` (Full row-by-row comparative dataset for in-depth statistical analysis).

---

## 6. Decision Criteria for Production Replacement

To safely declare Master V2 (or an exported INT8 variant) as the new production model, the field evaluation must meet the following criteria:

1. **Sample Size:** At least 50 distinct physical captures across >= 10 unique Braille documents.
2. **Macro CER Delta:** Mean raw CER for V2 must be strictly lower than V1 ($\Delta \text{CER} < 0.0$).
3. **Statistical Significance:** Paired two-tailed t-test or Wilcoxon signed-rank test on per-sample CER achieving $p < 0.05$.
4. **Duplicate Suppression Verification:** Over-detection / duplicate insertion rate on physical paper must not exceed V1 baseline.
5. **On-Device Runtime Parity:** Exported INT8 TFLite model must execute under 200 ms on target Android test devices without UI thread stutter.
