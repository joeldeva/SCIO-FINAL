# Sciobraille V2 Android Test Build Report

**Date:** 2026-09-24
**Git Branch:** `feat/v2-master-model`
**Build Target:** `app-v2Test.apk` (Variant: `v2Test`)
**Gradle Task:** `:app:assembleV2Test` (with `testV2TestUnitTest` passed)

---

## 1. Artifact Verification & Build Metadata

| Property | Value | Notes |
|---|---|---|
| **Local File Path** | [`sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk) | Generated via Gradle 9.0.0 |
| **File Size** | 62,911,813 bytes (60.00 MB) | Full debug packaging |
| **SHA-256** | `9497c7637764d87937497eee9fe7687e6d0160fdd0625db9020614ad5e1c6ec4` | Cryptographically verified |
| **Application ID** | `com.sciobraille.scanner.v2test` | Distinct from production `com.sciobraille.scanner` |
| **Application Label** | `Sciobraille V2 Test` | Verified in AAPT manifest dump |
| **Version Name** | `1.0.0-v2test` | Appended suffix |
| **Version Code** | `1` | Matches base release code |
| **Bundled Offline Model** | `best_v2_int8.tflite` | 11.02 MB INT8 quantized model |
| **Model Checksum** | `7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c` | Exact Master V2 INT8 export |

---

## 2. Safety Invariants & Side-by-Side Isolation

1. **Production Assets Unchanged:**
   - Production TFLite model [`sciobraille-scanner/android/app/src/main/assets/best_int8.tflite`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-scanner/android/app/src/main/assets/best_int8.tflite) (SHA-256: `9f6c45865ed2421041e8e46c865604ef953987382336c92bca91092d8eb5f4ad`) was **not modified or replaced**.
   - Production backend checkpoint [`sciobraille-scanner/backend/model/best.pt`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-scanner/backend/model/best.pt) (SHA-256: `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`) was **not modified or replaced**.
   - Release signing credentials in `signingConfigs.upload` remain untouched.
2. **Dual-Install Guarantee:**
   - Because `v2Test` uses `applicationIdSuffix ".v2test"`, Android treats this build as a completely separate application (`com.sciobraille.scanner.v2test`).
   - Installing `app-v2Test.apk` on a phone that already has the production Sciobraille app will **NOT** overwrite, replace, or wipe the production app.
   - The production Room SQLite database (`sciobraille_scanner.db` / `lms_progress.db`) and user scan history are fully isolated in separate Android data sandboxes.
3. **Dual Application Labels & Icons:**
   - Production App: App Label = `Sciobraille Scanner`, Header = `ScioBraille`
   - Test App: App Label = `Sciobraille V2 Test`, Header = `ScioBraille V2 Test`

---

## 3. Online V2 Backend Configuration

For testing V2 online recognition without disturbing production:

1. **Independent Port Allocation:**
   - Production Backend: Port `8088` (launched via `sciobraille-scanner/backend/start_backend.bat`).
   - V2 Test Backend: Port `8089` (launched via [`sciobraille-scanner/backend/start_v2_backend.bat`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/sciobraille-scanner/backend/start_v2_backend.bat)).
2. **Running the V2 Test Backend:**
   ```bash
   cd sciobraille-scanner/backend
   start_v2_backend.bat
   ```
   Or via command line:
   ```bash
   set BRAILLE_PORT=8089
   set MODEL_PATH=../../sciobraille-model-lab/models/v2_master/best.pt
   python scanner_api.py
   ```
3. **Configuring the Android Test App for Online V2:**
   Add to `sciobraille-scanner/android/local.properties`:
   ```properties
   SCIOBRAILLE_V2_BACKEND_URL=http://<YOUR_LAPTOP_IP>:8089
   ```
   Rebuilding `assembleV2Test` will automatically point the test app's WebSocket to port `8089`.

---

## 4. Installation & Sideloading Instructions

### Method A: Direct ADB Install (Recommended if phone connected via USB)
1. Enable **Developer Options** and **USB Debugging** on the target Android phone.
2. Connect the phone via USB and check device status:
   ```bash
   adb devices
   ```
3. Install the APK:
   ```bash
   adb install -r sciobraille-scanner/android/app/build/outputs/apk/v2Test/app-v2Test.apk
   ```

### Method B: Direct File Transfer (Wireless / USB Drive)
1. Copy `app-v2Test.apk` to phone storage (via Google Drive, USB transfer, or messaging).
2. Open the file on the phone and tap **Install**.
3. If prompted, grant permission to "Install unknown apps" for the file manager.

---

## 5. Hardware & Device Status Report

* **Android SDK Environment:** Verified (`C:\Users\devaj\AppData\Local\Android\Sdk`, Build Tools `36.1.0`, Compile SDK `36`, Min SDK `26`).
* **Active ADB Devices:** Currently `0` devices attached (`List of devices attached` empty).
* **Execution Status:** Build, unit testing, and APK packaging completed 100% successfully on desktop; physical-phone testing awaits hardware connection by the user according to [`reports/v2_device_testing_checklist.md`](file:///c:/Users/devaj/OneDrive/Documents/BRAILLEVISION/reports/v2_device_testing_checklist.md).
