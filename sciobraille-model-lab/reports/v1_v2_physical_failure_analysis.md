# Sciobraille V1 vs V2 Physical Failure Analysis

**Date:** 2026-09-24
**Evaluator:** Automated Physical Investigation Suite (`sciobraille-model-lab/scripts/investigate_physical_regression.py`)
**Pipeline Configuration:** Identical preprocessing, inference confidence (`conf=0.25`), IoU NMS (`iou=0.45`), duplicate suppression (`duplicate_iou=0.70`), and line reconstruction parameters.

---

## 1. Executive Summary

A granular investigation was conducted comparing the production baseline **V1** (`sciobraille-scanner/backend/model/best.pt`) and the newly trained **V2 Master** (`sciobraille-model-lab/models/v2_master/best.pt`) across the 3 physical benchmark photographs:
1. `scio_known_01` (Clean multi-line Braille sheet)
2. `dmi_root_01` (Unflipped, 180° physically inverted capture)
3. `dmi_flipped_01` (Pre-rotated, properly oriented capture)

### Primary Root Cause Finding
The regression observed on the physical benchmark (V2 macro CER 0.396 vs V1 macro CER 0.352; readable CER 0.094 vs 0.028) is **primarily driven by detection sensitivity and duplicate bounding-box emissions on embossed paper artifacts**, rather than classification failure or text reconstruction errors:
* **Higher Recall / Over-Detection:** V2 was trained on the Unified Master V2 dataset with extensive data augmentation, resulting in a significantly more sensitive detector. On physical paper, embossed dot shadows and paper wrinkles trigger secondary bounding boxes that pass NMS (`iou=0.45`) and default duplicate suppression (`duplicate_iou=0.70`), producing inserted characters (e.g. `"eindia"`, `"collegee"`, `"engineeirwin"`).
* **True Recall Benefit:** On `scio_known_01`, V2 correctly recovered the faint cell `'v'` in `"visually impaired"` (confidence `0.735`), which V1 completely failed to detect (transcribing `"isually impaired"`).
* **Orientation Dependency:** Both models fail completely (CER = 1.0) on `dmi_root_01` because the photograph was taken upside down and the default configuration does not apply horizontal rotation flips (`flip_strategy: never`).

---

## 2. Granular Per-Image Comparison

### 2.1 Image 1: `scio_known_01`

* **Ground Truth:**
  ```text
  jaihind
  india
  sciobraille
  visually impaired
  great project
  ```
* **Visual Annotations:**
  - V1 Detections: [scio_known_01_v1.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/scio_known_01_v1.png)
  - V2 Detections: [scio_known_01_v2.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/scio_known_01_v2.png)
  - Side-by-Side Comparison: [scio_known_01_comparison.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/scio_known_01_comparison.png)

#### Quantitative Metrics
| Metric | V1 Baseline | V2 Master | Delta (V2 - V1) |
|---|---|---|---|
| **Raw Text** | `jaihind\nindia\nsciobraille\nisually impaired\ngreat project` | `jaihfnd\neindia\nsciobraille\nvisually impaired\ngreat project` | - |
| **Character Error Rate (CER)** | 1.75% (1 / 57) | 3.51% (2 / 57) | +1.76% |
| **Word Error Rate (WER)** | 14.29% (1 / 7) | 28.57% (2 / 7) | +14.28% |
| **Total Detected Cells** | 53 | 58 | +5 cells |
| **Duplicate Pairs (> 0.70 IoU)** | 3 | 6 | +3 pairs |
| **Confidence: Mean ± Std** | 0.854 ± 0.073 | 0.804 ± 0.088 | -0.050 |
| **Confidence: Min / Max** | 0.522 / 0.927 | 0.527 / 0.932 | - |

#### Granular Error Decomposition
1. **Missing Cells:**
   - **V1:** Missed the leading cell `'v'` at `x ≈ 138, y ≈ 343` in `"visually impaired"`, producing `"isually impaired"`.
   - **V2:** Correctly detected cell `'v'` (`label=v`, `conf=0.735`, `bbox=[115.0, 312.6, 162.7, 374.9]`).
2. **Duplicate Detections / Artifact Insertions:**
   - **V2:** Inserted an extra cell `'e'` (`conf=0.678`, `bbox=[285.5, 153.4, 318.3, 206.9]`) directly adjacent to the true cell `'i'` (`conf=0.783`, `bbox=[280.8, 150.4, 324.0, 210.2]`). The IoU between these overlapping predictions was 0.612, which escaped the default `duplicate_iou: 0.70` suppression filter and emitted `"eindia"`.
3. **Class Misclassifications:**
   - **V2:** In the first line `"jaihind"`, V2 predicted cell 5 as `'f'` (`conf=0.932`) instead of `'i'` (`conf=0.786`), yielding `"jaihfnd"`. Shadowing across the top right dot of the cell inverted the perceived dot pattern.
4. **Reading Order & Spacing:**
   - Line segmentation correctly grouped all 5 lines in both models.
   - Horizontal reading order was preserved perfectly across all lines.
   - Word spacing correctly split `"visually impaired"` and `"great project"`.

---

### 2.2 Image 2: `dmi_root_01`

* **Ground Truth:**
  ```text
  dmi college
  of engineering
  ```
* **Visual Annotations:**
  - V1 Detections: [dmi_root_01_v1.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_root_01_v1.png)
  - V2 Detections: [dmi_root_01_v2.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_root_01_v2.png)
  - Side-by-Side Comparison: [dmi_root_01_comparison.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_root_01_comparison.png)

#### Quantitative Metrics
| Metric | V1 Baseline | V2 Master | Delta (V2 - V1) |
|---|---|---|---|
| **Raw Text** | `""` (Empty string) | `""` (Empty string) | 0.0 |
| **Character Error Rate (CER)** | 100.0% (26 / 26) | 100.0% (26 / 26) | 0.0 |
| **Word Error Rate (WER)** | 100.0% (4 / 4) | 100.0% (4 / 4) | 0.0 |
| **Total Detected Cells** | 0 | 0 | 0 |
| **Confidence: Mean** | 0.0 | 0.0 | 0.0 |

#### Granular Error Decomposition
1. **Horizontal Orientation / Inversion:**
   - The photograph `dmi_root_01` was captured upside down (180° rotated relative to standard Braille orientation).
   - In standard Grade 1 Braille, dot patterns inverted upside down do not correspond to recognizable anchor patterns for either model.
   - Under `flip_strategy: never`, the scanner does not evaluate rotated orientations, resulting in 0 detected cells for both V1 and V2.
   - **Conclusion:** Both models are invariant in their complete failure when image orientation is inverted.

---

### 2.3 Image 3: `dmi_flipped_01`

* **Ground Truth:**
  ```text
  dmi college
  of engineering
  ```
* **Visual Annotations:**
  - V1 Detections: [dmi_flipped_01_v1.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_flipped_01_v1.png)
  - V2 Detections: [dmi_flipped_01_v2.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_flipped_01_v2.png)
  - Side-by-Side Comparison: [dmi_flipped_01_comparison.png](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-model-lab/reports/visualizations/physical_benchmark/dmi_flipped_01_comparison.png)

#### Quantitative Metrics
| Metric | V1 Baseline | V2 Master | Delta (V2 - V1) |
|---|---|---|---|
| **Raw Text** | `dmi college\nof engineerin` | `dmi collegee\nof engineeirwin` | - |
| **Character Error Rate (CER)** | 3.85% (1 / 26) | 15.38% (4 / 26) | +11.53% |
| **Word Error Rate (WER)** | 25.0% (1 / 4) | 50.0% (2 / 4) | +25.0% |
| **Total Detected Cells** | 23 | 32 | +9 cells |
| **Duplicate Pairs (> 0.70 IoU)** | 1 | 7 | +6 pairs |
| **Confidence: Mean ± Std** | 0.845 ± 0.047 | 0.791 ± 0.068 | -0.054 |
| **Confidence: Min / Max** | 0.652 / 0.885 | 0.632 / 0.881 | - |

#### Granular Error Decomposition
1. **Missing Cells:**
   - **V1:** Missed the terminal cell `'g'` at the far right boundary of `"engineering"`, producing `"of engineerin"`.
   - **V2:** Detected cells at the terminal boundary, but generated multi-class overlapping detections (`'w'` and `'r'`).
2. **Duplicate Box Clusters:**
   - In `"college"`, the final cell `'e'` generated two valid bounding boxes:
     - Box A: `x=1131.9, y=415.0, label=e, conf=0.786`
     - Box B: `x=1127.1, y=413.1, label=e, conf=0.681`
     - IoU was 0.627 (below 0.70 threshold), emitting `"collegee"`.
   - In `"engineering"`, V2 generated 3 separate duplicate clusters:
     - At `x ≈ 939-943`: double detection of `'e'` (`conf=0.799`) and `'i'` (`conf=0.728`), producing `"engineeir..."`.
     - At `x ≈ 1003-1008`: overlapping detections of `'w'` (`conf=0.881`) and `'r'` (`conf=0.831`), producing `"...irwin"`.
3. **Class Misclassifications:**
   - Because physical embossing on this sheet has shallow depth and diffuse lighting, dots 1, 2, 4, 5, 6 cast shadows that V2 interprets as candidate letters with 0.63-0.88 confidence.
4. **Reading Order & Spacing:**
   - Line segmentation correctly separated line 1 (Y ≈ 395-410) and line 2 (Y ≈ 495-520).
   - Word spacing correctly recognized the intra-word spaces between `"dmi"` and `"college"`, and `"of"` and `"engineering"`.

---

## 3. Systematic Component Breakdown

| Pipeline Stage | V2 Behavior vs V1 | Impact on Regression | Root Cause Summary |
|---|---|---|---|
| **1. Detection & Sensitivity** | **Substantially Higher Sensitivity** (+7.5% recall on val/test) | **CRITICAL (Primary Cause)** | Generates dense candidate proposals. Paper embossing shadows produce secondary boxes that evade default IoU=0.70 duplicate suppression. |
| **2. Class Recognition** | **Similar Accuracy** (mAP50-95 ~0.76) | **MODERATE** | In localized shadow regions, dots blur together causing confusions (e.g. `'i'` vs `'f'`, `'r'` vs `'w'`). |
| **3. Horizontal Orientation** | **Identical Behavior** (0 detections on 180° inverted) | **NEUTRAL** | Neither model handles 180° inversion without upstream rotation or multi-pass orientation search. |
| **4. Text Reconstruction** | **Identical Logic** (Y-clustering + X-sorting + spacing) | **LOW (Secondary Symptom)** | The reconstruction algorithm performs as designed; it is forced to emit duplicate characters because upstream suppression passed multiple valid boxes for a single physical cell. |

---

## 4. Key Takeaways & Constraints

1. **Benchmark Sample Bias:**
   - The current physical benchmark consists of only 3 photographs, one of which is 180° inverted (`dmi_root_01`).
   - Consequently, **only 2 readable images** dictate the benchmark metrics. An extra duplicate box in 2 words swings macro WER by 25%.
2. **Preservation of Pipeline Parameters:**
   - As mandated by the protocol, **no heuristic thresholds (`conf`, `iou`, `duplicate_iou`) were modified** to favor V2.
3. **Production Winner Recommendation:**
   - Neither model should be declared a production winner based on these 3 images.
   - A statistically rigorous evaluation on a representative, independent physical dataset (50-100 images) must be conducted using the newly prepared field testing workflow.
