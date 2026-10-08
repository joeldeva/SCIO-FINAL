# Sciobraille V2 Physical Phone Testing Checklist & Protocol

**Protocol Version:** 1.0.0
**Target Build:** `Sciobraille V2 Test` (`com.sciobraille.scanner.v2test`)
**Production Baseline:** `Sciobraille Scanner` (`com.sciobraille.scanner`)
**APK Location:** [`sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk)

---

## 1. Physical Device Preparation & Side-by-Side Verification

- [ ] **Step 1.1: Enable Developer Mode & USB Debugging**
  - Settings $\rightarrow$ About Phone $\rightarrow$ Tap "Build number" 7 times.
  - Settings $\rightarrow$ System $\rightarrow$ Developer options $\rightarrow$ Enable "USB debugging".
- [ ] **Step 1.2: Install V2 Test Build Alongside Production**
  - Execute:
    ```bash
    adb install -r sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk
    ```
- [ ] **Step 1.3: Confirm Dual App Isolation on Home Screen**
  - Check that the phone launcher displays **two separate app icons**:
    1. **Sciobraille Scanner** (`com.sciobraille.scanner`, Production V1)
    2. **Sciobraille V2 Test** (`com.sciobraille.scanner.v2test`, Master V2 INT8)
  - Verify that opening the Test build displays the header: `ScioBraille V2 Test`.
  - Verify that existing history or lesson progress in the production app is intact.

---

## 2. Core Functional Test Procedures

### Test 1: Camera Permission & Preview Stream
- [ ] Launch `Sciobraille V2 Test`.
- [ ] Confirm system camera permission dialog appears on first launch.
- [ ] Grant "While using the app" permission.
- [ ] Verify live CameraX preview stream starts immediately without black screen, stutter, or aspect-ratio distortion.
- [ ] Tap "Flash" button; verify camera torch activates and deactivates reliably.

### Test 2: Offline Scanning (V1 vs V2 Comparison)
- [ ] Place device in **Airplane Mode** (disable Wi-Fi and Cellular).
- [ ] Aim camera at a physical Braille document.
- [ ] Tap "Scan".
- [ ] Check on-screen diagnostic stats bar:
  - Form: `<N> cells (<D> dups filtered) / <Confidence>%`
  - Check Logcat (`adb logcat -s SciobrailleOffline`):
    ```text
    Model: best_v2_int8.tflite, Parsed: <N_raw>, Suppressed: <N_dup>, Kept: <N_nms>
    ```
- [ ] Compare recognition output on the exact same document between Production App (V1) and Test App (V2).

### Test 3: Online V2 Scanning (Port 8089)
- [ ] On the development PC on the same local Wi-Fi, start the V2 backend:
  ```cmd
  sciobraille-scanner\backend\start_v2_backend.bat
  ```
- [ ] Confirm terminal logs: `Starting Sciobraille V2 Test Backend on port 8089...`
- [ ] Connect the phone to the local Wi-Fi.
- [ ] Tap "Scan" in online mode; confirm frame transmission over WebSocket to port `8089`.

### Test 4: Physical Orientation & Contrast Handling
- [ ] **Front-Embossed Reading:**
  - Photograph raised dots under standard overhead lighting.
  - Verify left-to-right character order matches standard Grade 1 Braille.
- [ ] **Back-Debossed / Inverted Paper Test:**
  - Photograph the reverse side of the page (depressions/punctures).
  - Note: Debossed Braille dots cast inverted shadows (negative contrast). Observe whether the detector recognizes debossed dots or requires illumination adjustment.
- [ ] **180° Inversion Test:**
  - Rotate physical document upside down.
  - Verify detector behavior (neither model detects cells upside down without pre-rotation, confirming invariant failure modes).

### Test 5: Inference Latency Benchmarking
- [ ] Using Logcat, capture 30 consecutive scan frame timings:
  ```bash
  adb logcat -s SciobrailleOffline | Select-String "inference_ms"
  ```
- [ ] Verify target latency criteria:
  - Average frame execution time $\le 200 \text{ ms}$ on modern mobile hardware (Snapdragon 7/8 series or MediaTek Dimensity).
  - UI thread remains responsive (no ANR or preview freeze during background TFLite execution).

### Test 6: Memory & Thermal Stress Profile
- [ ] Run continuous scanning loop for **5 minutes**.
- [ ] Monitor memory footprint via ADB:
  ```bash
  adb shell dumpsys meminfo com.sciobraille.scanner.v2test
  ```
- [ ] Verify:
  - Native heap remains stable ($\le 180 \text{ MB}$, no memory leak from unclosed Bitmaps or ByteBuffers).
  - Device does not experience extreme thermal throttling or frame rate drops below 15 fps.

### Test 7: App Restart & History Persistence
- [ ] Perform 3 scans and ensure results appear on the Scanner screen.
- [ ] Force-close the app (`adb shell am force-stop com.sciobraille.scanner.v2test`).
- [ ] Reopen `Sciobraille V2 Test`.
- [ ] Navigate to the "History" tab; confirm all 3 scan records are preserved in the Room database.
- [ ] Open the production `Sciobraille Scanner` app; confirm its history is completely independent and uncorrupted.

---

## 3. Real-World Field Validation Protocol (50–100 Physical Images)

To statistically determine whether V2 should replace V1 in a future update, execute field testing following these rules:

### Dataset Requirements
* **Volume:** 50 to 100 distinct physical Braille photographs.
* **Document Diversity:** At least 10 different physical Braille sheets, books, cards, or signs.
* **Avoid Repetition:** Do NOT take 50 photographs of the same page from slightly different millimeter distances.
* **Environmental Matrix:**
  * 25% Ambient diffuse room light
  * 25% Direct overhead / flashlight illumination
  * 25% Grazing side illumination (high shadow contrast)
  * 25% Dim / low-light or angled perspective (10°–30° tilt)

### Ground Truth Recording
Record every test photo in `sciobraille-model-lab/benchmark/independent_physical/manifests/field_test.csv` using the schema:
```csv
id,image_path,ground_truth_transcription,document_id,capture_group_id,orientation,lighting,blur,distance,perspective,line_count,notes
```

### Running the Comparative Benchmark
Execute the automated harness:
```bash
python sciobraille-model-lab/scripts/evaluate_field_samples.py \
    --manifest sciobraille-model-lab/benchmark/independent_physical/manifests/field_test.csv \
    --output-dir sciobraille-model-lab/reports/field_evaluation
```

### Production Promotion Criteria
V2 may only be considered for production replacement if:
1. $\Delta \text{CER} < 0.0$ (Raw Character Error Rate strictly lower than V1).
2. $p < 0.05$ under a paired two-tailed t-test or Wilcoxon signed-rank test.
3. Over-detection duplicate rate on physical embossed paper is confirmed equal to or lower than V1.
