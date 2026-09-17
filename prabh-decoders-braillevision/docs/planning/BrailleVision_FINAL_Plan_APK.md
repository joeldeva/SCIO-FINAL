# BrailleVision — FINAL Execution Plan (On-Device APK)

**Chosen path:** a real, downloadable **Android APK** that reads embossed Braille with the phone camera, fully **on-device and offline**, and speaks the text. Built on the **official Ultralytics YOLO Flutter plugin**, trained on **both Kaggle accounts in parallel**.

**Safety net (keep alive the whole time):** the Gradio web app (`app_web.py`) is your guaranteed fallback — a free Hugging Face Space is ~15 minutes to deploy and also runs on a phone browser. If the Flutter toolchain fights you, you ship the web app and lose nothing. **Never end with no working demo.**

**The one rule:** the judges score your **video**. A working on-device APK demo recorded by Hour 11 beats a perfect build you never recorded. **Hard feature freeze at Hour 9.**

---

## 1. Architecture

```
Phone camera (live)
   │
   ▼
YOLOView  (Ultralytics YOLO Flutter plugin, on-device)
   │   runs your fine-tuned cell-classifier as a .tflite model
   ▼
onResult: list of { className=letter, confidence, boundingBox }
   │
   ▼
Decode (Dart):  sort detections left→right (group lines by y) → join classNames → word/line
   │
   ▼
Display big high-contrast text   +   speak via flutter_tts
```

Model job: detect each Braille **cell** and classify it as a **letter** (Grade-1, A–Z). Decode is just "sort the boxes, read the labels" — no grid geometry, no liblouis. That keeps it foolproof in a 12-hour window.

---

## 2. Datasets (researched — use these)

Your pipeline needs **detection** data: images where each Braille **cell is boxed and labelled with its letter**, in YOLO format. Primary source is Roboflow Universe (one-click YOLO export, downloads straight into training). Supplement with real-photo sets for robustness, and **your own rig photos** for the test distribution.

### Detection datasets — train on these
| Dataset | Size | Link | Use |
|---|---|---|---|
| **Braille Detection** (yapayzeka), Roboflow Universe | 1,324 imgs, per-letter boxes | `https://universe.roboflow.com/yapayzeka/braille-detection-vxtp1` | **Primary.** YOLO export + a pre-trained model |
| More braille-letter sets, Roboflow Universe search | varies | `https://universe.roboflow.com/search?q=braille` | Merge a couple for variety |
| **Angelina Braille Images Dataset** | ~240+ real photos | `https://github.com/IlyaOvodov/AngelinaDataset` | Real-world lighting/perspective |
| **DSBI** (Double-Sided Braille Image) | real pages, dot+cell labels | search "DSBI braille dataset github" | Real pages, double-sided |
| **DotNeuralNet** | Angelina+DSBI+natural+Kaggle, **pre-merged YOLO format** + pretrained YOLOv5/v8 weights | `https://github.com/snoop2head/DotNeuralNet` | Fast warm-start |

> ⚠️ **Do NOT use the "braille block" datasets** on Roboflow (e.g. "braille-block-detect"). Those are the yellow tactile **paving tiles** for sidewalks — street navigation, not Braille text. Wrong problem.

### Classification datasets — NOT for YOLO detection (no boxes); baseline/synthetic only
- Kaggle **Braille Character Dataset** (shanks0465): `https://www.kaggle.com/datasets/shanks0465/braille-character-dataset` — ~1,560 single-char 28×28 images, A–Z.
- Similar: `mdismielhossenabir/braille-character-image-classification`, `adviksharma/braille-images-for-english-characters`.

### Your own data — the highest-value set
Capture **50–150 photos** of your page under the rig (varied position/distance/light), label in **Roboflow** with **model-assisted labeling** (run the yapayzeka pre-trained model, correct its guesses — fast). Hold out **10–30** images as a test set the models never see.

**Recommended training mix:** yapayzeka (base) + a few of your own captures (domain match) → fine-tune. Add Angelina/DotNeuralNet if time allows.

---

## 3. Training — both Kaggle accounts in parallel

Each account = one GPU session = one experiment, both with background execution. Compare on **your** held-out photos, ship the winner, keep A as the floor.

- **Account A — SAFE:** warm-start from the **yapayzeka pre-trained / your existing weights**, fine-tune on yapayzeka + your captures. `yolo26n`, default aug. Guaranteed-decent model.
- **Account B — PUSH:** fresh `yolo26s`, heavy augmentation, same data. Tries to beat A on robustness.

Both finish in well under an hour for a nano/small model. Then **export to TFLite** for the phone:
```bash
yolo export model=best.pt format=tflite int8=True imgsz=640
```
> The Flutter plugin is **strict about export parameters** — use the exact export command from the plugin's README (`github.com/ultralytics/yolo-flutter-app`). Keep the produced `.tflite` **and its metadata `.yaml`** together.

---

## 4. The APK build path (Flutter + Ultralytics plugin)

Don't build from scratch — fork the plugin's example app and swap in your model.

1. **Toolchain:** install Flutter + Android SDK; enable USB debugging on an Android phone (or use an emulator). Verify with `flutter doctor`.
2. **Base app:** clone `github.com/ultralytics/yolo-flutter-app`; open the `example/` app; `flutter pub add flutter_tts`.
3. **Validate on-device FIRST** with a **stock** model (`modelPath: 'yolo11n'`): confirm camera + live detection runs on the phone before touching your model. *(This is your critical de-risking gate.)*
4. **Swap in your model:** put your `best_int8.tflite` (+ metadata `.yaml`) in `example/assets/models/`; point `YOLOView(modelPath: 'assets/models/best_int8.tflite', task: YOLOTask.detect)`.
5. **Decode + speak:** in `onResult`, sort detections by `boundingBox` x (group lines by y), concatenate `className` into a string, speak it with `flutter_tts` (debounced so it doesn't repeat every frame).
6. **Accessible UI:** big high-contrast reading text, a "🔊 Speak" button, an audible "scanning/ready" cue.
7. **Build + distribute:**
   ```bash
   flutter build apk --release
   ```
   Upload `build/app/outputs/flutter-apk/app-release.apk` to a **GitHub Release** for download. No Play Store needed.

Runs ~30 FPS on a modern phone, fully offline — the strongest accessibility/impact story.

---

## 5. Roles (merge if fewer than 3)

- **MOBILE:** Flutter toolchain → example app on the phone (stock model) → swap in trained model → decode + TTS + UI → build APK. Owns the critical gate.
- **DATA:** rig + capture + label in Roboflow + held-out test set.
- **KAGGLE:** both accounts (A/B) → train → TFLite export → hand weights to MOBILE. Also keeps the **web-app Space ready** as the fallback.

Everyone commits to the public repo; commit every 1–2 hours (timestamps are checked).

---

## 6. Hour-by-hour (anchor to your remaining time; the GATES matter more than the clock)

### H0–0.5 · War room
Build the **oblique-light rig** (LED low and to the side so dots cast shadows — the #1 accuracy win). MOBILE starts Flutter install. KAGGLE opens both notebooks (GPU + Internet ON) and starts the yapayzeka download. First repo commit.

### H0.5–2 · De-risk the hardest unknown
MOBILE: get the **stock** Ultralytics example app running **on the phone** with live detection.
**GATE @ H2 — does the example app detect on the phone?**
- **YES →** proceed.
- **NO (toolchain stuck) →** switch to the **web-app fallback**: deploy `app_web.py` to a HF Space (~15 min). Don't burn more than ~30 extra min fighting Flutter.
DATA: capture + start labeling. KAGGLE: launch Account A training.

### H2–6 · Train + custom model on device
KAGGLE: A fine-tuning; launch B; export both to TFLite. DATA: finish labels; **lock the held-out test set**. MOBILE: once weights arrive, swap the `.tflite` into the app.
**GATE @ H6 — does YOUR model detect Braille letters on the phone?**
- **YES →** add decode + TTS.
- **NO →** export the **yapayzeka pre-trained** model to TFLite and use that; else fall back to the web app.

### H6–9 · Decode, speak, polish
MOBILE: `onResult` decode (sort → string) + `flutter_tts` + accessible UI + audible cues. KAGGLE: run `evaluate.py` on both A/B over the held-out set → pick the winner honestly.
**GATE @ H9 — FEATURE FREEZE.** Whatever runs now is the demo.

### H9–11 · Build, record, document
`flutter build apk --release` → upload to a GitHub Release. **Record the demo video** (phone reading real paper → live decode → speech). Finalize README, TOOLS.md, LICENSE (AGPL-3.0). Verify a fresh install of the APK works.

### H11–12 · Buffer + submit
Final commit, push, submit (repo + APK release link + video). Re-watch the video. **Stop.**

---

## 7. Fallback ladder (read when stuck — you always have a working artifact)

1. **Flutter toolchain won't come up (H2)** → deploy the **web app** (`app_web.py` → HF Space). Open on phone = phone camera. Guaranteed.
2. **Your trained model fails on device (H6)** → use the **yapayzeka pre-trained** braille model (TFLite) → if still failing, web app.
3. **APK build/sign fails (H10)** → record the video against the app running via `flutter run` on the phone (debug build), or against the web app. A clean recording beats a release-build chase.
4. **Out of time** → submit the web-app URL + repo + honest README. A working Grade-1 reader with a clean video scores on every criterion.

The web app stays deployable throughout — that's the floor under everything.

---

## 8. Evaluation (honest, on held-out data)

Before TFLite export, run `evaluate.py` on your held-out photos for A and B: **exact-match %**, **mean CER**, and on-device **FPS** (visible in the app). Don't tune on the test set; don't demo only your one lucky page. Put the numbers in the README.

---

## 9. Repo, distribution, licensing

```
braillevision/
├── README.md          # what / install APK / results table / video + APK links
├── LICENSE            # AGPL-3.0 (Ultralytics dependency)
├── TOOLS.md           # AI / vibe-coding tools disclosure (REQUIRED)
├── train_kaggle.py    # training, both accounts, + TFLite export
├── evaluate.py        # held-out metrics
├── app_web.py         # web-app fallback
├── flutter_app/       # the forked example app with your model + decode + TTS
│   └── assets/models/best_int8.tflite (+ .yaml)
├── data/README.md     # dataset sources + licenses (links above)
├── test/              # held-out images + labels.csv
└── docs/rig.md        # capture-rig photo + setup
```
- **APK distribution:** GitHub Release asset (link it in the README).
- **License:** AGPL-3.0 for the repo (Ultralytics YOLO + the Flutter plugin are AGPL-3.0). State it in the README.
- **TOOLS.md:** list every AI/vibe-coding tool used — required by the brief.

---

## 10. Demo video (this is what's judged)

2–3 min: (1) the embossed paper in hand — clearly real bump-paper; (2) the **phone app** with live detection overlay; (3) decoded text on screen; (4) **speech** playing aloud; (5) one hard case (rotated/dim page); (6) close on impact — offline, on-device, low-cost, usable independently by a blind person — plus your honest accuracy. If the release APK is flaky, record the app via `flutter run`.

---

## 11. Submission checklist (final 30 min)

- [ ] Public GitHub repo, builds from a fresh clone
- [ ] **APK** on a GitHub Release (+ link in README) — or web-app URL if you fell back
- [ ] README: install steps, results table (exact-match/CER/FPS), rig photo, video link
- [ ] **TOOLS.md** (AI-tool disclosure) + **LICENSE** (AGPL-3.0)
- [ ] `data/README.md` with dataset sources + licenses
- [ ] Demo video: real paper → on-device decode → speech
- [ ] Steady git commits across the 12 hours
- [ ] Submitted, then stop

---

## 12. Judging-criteria coverage

| Criterion | Covered by |
|---|---|
| Physical recognition accuracy | Oblique-light rig + fine-tuned model on real + own data + honest held-out eval |
| Real-time performance | On-device TFLite via YOLOView (~30 FPS), int8-quantized nano model |
| Technical implementation | Trained YOLO → TFLite → native plugin; clean decode + TTS; tested |
| Robustness | Varied-lighting/position data; debounced temporal output; hard case in demo |
| Accessibility & UX | Fully offline on the user's own phone; audio output; high-contrast text; audible cues |
| Innovation & impact | On-device, offline, zero-cost Braille reader anyone can install — the rig-physics insight |
| Demo & submission | Downloadable APK + repo + README + metrics + tooling disclosure + clear video |

---

## 13. What I'll build the moment you approve

1. **`train_kaggle.py`** (updated) — Roboflow (yapayzeka) download snippet + your-captures merge + train + **TFLite int8 export**; one variable flips it between Account A (safe warm-start) and Account B (yolo26s + heavy aug).
2. **Flutter source to drop into the example app:**
   - `main.dart` / inference screen — `YOLOView` + the **decode** (sort → string) + **flutter_tts** speak (debounced) + accessible UI.
   - `pubspec.yaml` additions (`ultralytics_yolo`, `flutter_tts`) + the Android assets/permissions setup.
   - the exact `flutter build apk` + GitHub-release commands.
3. **`evaluate.py`** — held-out exact-match / CER / FPS, to pick A vs B before export.
4. **Repo docs** — `README.md` (with APK install + results + video), `TOOLS.md`, `LICENSE`, `data/README.md`.

**Reply "go" and I'll start with `train_kaggle.py` + the Flutter inference screen (the two on the critical path), then the rest.** Tell me your model's class list if it's not plain A–Z (e.g. includes space/numbers), and whether you have Flutter already installed so I can tune the toolchain steps.
