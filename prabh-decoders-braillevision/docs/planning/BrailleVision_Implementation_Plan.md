# BrailleVision 2026 — Implementation Plan

Real-time camera reading of **physical embossed/handwritten Braille → English text + speech.**

---

## 0. The one-paragraph version

The single highest-leverage decision is *not* the model — it's **controlling the capture and decoupling vision from language.** Build the core as a three-part pipeline: (1) a **dot detector** (YOLO) that finds individual raised dots, which is a far easier and more data-efficient problem than classifying whole cells; (2) a **geometric grid reconstructor** that snaps detected dots onto the fixed 2×3 Braille lattice and reads each cell as a 6-bit pattern; (3) a **deterministic decoder** (6-bit → Unicode Braille → `liblouis` back-translation) that produces text, then speech. Pair this with a **cheap oblique-lighting capture rig** so the colorless dots actually cast shadows. This architecture wins on the two criteria most submissions fail: **robustness in real-world conditions** and **honest accuracy**, because it degrades gracefully and is fully debuggable.

Your existing prototype (the YOLO cell-classifier in the screenshot) is a **valid baseline** — keep it, but make the dot-detection pipeline the primary system and compare the two.

---

## 1. Why this architecture (read before coding)

There are two viable paradigms. Understanding the trade-off is the most important technical decision you'll make.

### Paradigm A — Direct cell classification (what your prototype does)
YOLO detects each Braille cell as one box and classifies it directly into a letter (`a`–`z`, etc.). Reading is trivial (sort boxes left-to-right, top-to-bottom).

- **Strength:** end-to-end, one model, dead-simple decode.
- **Weakness:** the model does *two* jobs at once (localize + identify a 6-dot pattern). Visually near-identical cells that differ by a single dot (e.g. `d`/`f`, `e`/`i`, `h`/`j`) get confused. It needs **balanced data across every class** — rare letters (`q`, `x`, `z`), capitals, numbers, and punctuation get few examples and low accuracy. This is almost certainly why your prototype shows moderate confidences (52–85%) and a garbled read. It also can't extend to numbers/contractions without retraining and relabeling.

### Paradigm B — Dot detection + geometric decode (recommended core)
YOLO detects **individual dots** (one class: `dot`). A geometric step reconstructs the grid and reads each cell. A deterministic table decodes patterns to text.

- **Strength:** detection is robust and extremely data-efficient — *every dot in every image is a positive example*, so a handful of labeled pages yields thousands of training instances. Decoding is deterministic, explainable, and trivially extends to numbers, punctuation, and Grade-2 contractions (just swap the decode table). When it's wrong, you know exactly whether it missed a dot or misgrouped a cell.
- **Weakness:** the grid-reconstruction logic is non-trivial (handles skew, perspective, variable spacing, missing dots). But that logic is *deterministic code you control*, not a black box you have to retrain.

### Decision
**Build B as the primary pipeline; keep A as a baseline/fallback.** B maps directly onto the judging criteria — it's the most robust, the most data-efficient (critical for a hackathon), the most debuggable (great for the demo and the AI code review), and it cleanly separates the **CV problem** (find dots) from the **language problem** (decode + contractions). This is also exactly the "OpenCV + ML in combination" the brief asks for: **YOLO** finds dots, **OpenCV/NumPy geometry** rebuilds the grid, **liblouis** decodes.

> Prior art validates this: Ovodov's *Angelina Braille Reader* (RetinaNet object detection over cells) and *DotNeuralNet* (YOLOv5/YOLOv8 over dots) are the two reference systems. We borrow the object-detection backbone from them but lean on the dot-level + geometric-decode variant for robustness and data efficiency.

---

## 2. The capture rig (do this first — it's the cheapest accuracy win)

Embossed Braille is **colorless** — white dots on white paper. Under flat, head-on lighting (like your third uploaded image), the dots are nearly invisible even to a human eye, and *no* model can recover signal that isn't in the pixels. The fix is physical, not algorithmic.

- **Oblique / raking light.** Place a small LED (a phone torch, a desk lamp, a cheap ring light with one side covered) **low and to one side**, so light grazes across the page. Each raised dot then casts a crisp little shadow — turning an invisible bump into a high-contrast dark-light blob. This single change can take you from ~50% to ~90%+ detection on embossed paper.
- **Fixed geometry.** Mount the camera (webcam or phone) on a stand at a **fixed height, roughly perpendicular** to the page. Consistent distance ⇒ consistent dot pitch in pixels ⇒ far easier and more reliable grid reconstruction.
- **Matte background, steady page.** A simple cardboard jig that holds the paper flat and at a fixed position removes most perspective and motion problems.

Document this rig in your README with a photo. Judges reward a team that understood the physics of the problem; many teams will fight the algorithm instead of fixing the lighting.

---

## 3. The pipeline, stage by stage

```
Camera frame
   │
   ▼
[1] Preprocess        grayscale → CLAHE contrast → denoise → (optional) perspective correction
   │
   ▼
[2] Dot detection     YOLO26-n / YOLO11-n, single class "dot"  →  list of (x, y) centroids + conf
   │
   ▼
[3] Grid reconstruct  deskew → estimate dot pitch → group into text-lines → snap to 2×3 lattice → cells
   │
   ▼
[4] Decode            each cell → 6-bit pattern → Unicode Braille (U+2800+mask) → liblouis back-translate → text
   │
   ▼
[5] Stabilize         majority vote over last K frames (temporal smoothing)
   │
   ▼
[6] Output            render text overlay + speak via TTS (debounced)
```

### [1] Preprocessing
`grayscale → CLAHE → light denoise`. **CLAHE** (Contrast-Limited Adaptive Histogram Equalization, `cv2.createCLAHE`) is the workhorse for low-contrast embossed dots — apply it before detection. Add optional **perspective correction**: detect the page quadrilateral (largest contour / corner markers) and warp to a flat top-down view; this normalizes dot pitch and makes the grid step much easier. Keep preprocessing cheap so you hold real-time frame rates.

### [2] Dot detection
- **Model:** `YOLO26-n` (nano) is the current Ultralytics release (Jan 2026) and is the right call here: it has **end-to-end NMS-free inference** and up to ~43% faster CPU inference, both of which matter for densely-packed dots and real-time webcam use. `YOLO11-n` is the stable fallback if you hit any YOLO26 ecosystem rough edges.
  - *Why NMS-free matters specifically for Braille:* dots sit very close together, and classic Non-Max-Suppression tends to wrongly merge neighboring boxes (Ovodov had to drop the IoU threshold to ~0.02 to cope). YOLO26 sidesteps that whole failure mode.
- **Classes:** a single class, `dot`. (Optional advanced variant: two classes, `recto_dot` / `verso_dot`, to handle double-sided pages — see Risks.)
- **Image size:** train/infer at 640 or 960; higher helps small dots if your frames are high-res.
- **Export for speed:** export to **ONNX / OpenVINO / TFLite** for faster CPU inference, or **CoreML/TFLite** if you target a phone.

```bash
# Train (after preparing data in YOLO format)
yolo detect train model=yolo26n.pt data=braille_dots.yaml epochs=120 imgsz=960 batch=16
# Export for fast CPU inference
yolo export model=runs/detect/train/weights/best.pt format=onnx
```

> ⚠️ **License note:** Ultralytics YOLO (incl. YOLO26/YOLO11/YOLOv5/v8) is **AGPL-3.0**. For a public hackathon repo that's fine — just license your repo compatibly (AGPL-3.0) and state it in the README. Disclose this in your tooling notes.

### [3] Grid reconstruction (the geometric core — your "secret sauce")
This deterministic step is what makes the system robust. Given the detected dot centroids:

1. **Deskew.** Braille lines are horizontal; estimate the small rotation that best aligns dots into rows (or rely on the perspective warp from step 1).
2. **Estimate the dot pitch.** Braille has fixed geometry: intra-cell dot spacing is uniform, the gap *between* adjacent cells is larger, and the gap *between lines* is larger still. Take nearest-neighbor distances between dots; the dominant small distance ≈ the intra-cell dot pitch in pixels. Everything else scales from this.
3. **Segment text-lines.** Cluster dots by *y* using the large vertical gaps to separate lines of Braille. (Each text-line spans **3 dot-rows** — top/middle/bottom of the cells.)
4. **Snap to an ideal lattice — the key robustness trick.** Rather than trusting raw clusters, overlay the *expected* 2×3 lattice (anchored by pitch and line baseline) and, for each of the 6 positions, check whether a detected dot lies within tolerance. Reading **occupancy against a known grid** means one missing/extra detection only flips one bit instead of corrupting the whole line.
5. **Form cells.** Within a line, the larger inter-cell horizontal gap delimits cell boundaries; assemble each cell's 6-bit pattern and preserve reading order (and spaces, inferred from extra-wide gaps).

Implement and unit-test this on **synthetic dot layouts first** (known input → known cells) before pointing it at the camera. It's pure geometry, so you can test it deterministically.

### [4] Decode
Standard Braille cell numbering:

```
1 • • 4
2 • • 5
3 • • 6
```

A filled set of dots → bitmask → Unicode Braille character `U+2800 + Σ 2^(dot−1)`, then `liblouis` back-translates the Braille string to text. `liblouis` is the standard open-source Braille translator/back-translator (it powers NVDA, JAWS, Orca), has **Python bindings**, and crucially handles **Grade-2 contractions** (where whole words map to single cells) which a naive letter-by-letter map cannot.

```python
# 6-bit pattern -> Unicode Braille
def dots_to_braille(dots):                 # dots: set like {1,2,4}
    mask = sum(1 << (d - 1) for d in dots)
    return chr(0x2800 + mask)

# Grade 1 (uncontracted) quick map for an MVP:
GRADE1 = {frozenset({1}): 'a', frozenset({1,2}): 'b', frozenset({1,4}): 'c',
          frozenset({1,4,5}): 'd', frozenset({1,5}): 'e', frozenset({1,2,4}): 'f', ...}

# Grade 2 (contracted) via liblouis — handles real-world contracted Braille:
import louis
text = louis.backTranslateString(["en-ueb-g2.ctb"], braille_unicode_string)
# (verify exact table names in your liblouis install: en-ueb-g1.ctb / en-ueb-g2.ctb;
#  you may need to prepend a display table such as "unicode.dis")
```

**Grade 1 vs Grade 2:** the Braille in your samples looks **uncontracted (Grade 1)** — letters map one-to-one. Target Grade 1 for your core demo (a simple dict is enough and is 100% reliable), and treat **Grade-2 via liblouis** as a clearly-scoped stretch goal. Don't let contraction complexity block a working Grade-1 demo.

### [5] Temporal stabilization
Don't trust a single frame — webcam frames have motion blur and focus drift. Two good options:
- **Majority voting:** decode every frame and emit the per-cell mode over the last *K* frames (e.g. K=5). Feels real-time and smooths out flicker.
- **Capture-when-stable:** monitor sharpness (variance of Laplacian) and motion; only decode when the frame is sharp and stationary. Cleaner output, slightly less "live."

Recommend **majority voting** for the live demo feel, with a sharpness gate to reject obviously blurry frames.

### [6] Output: text + speech
- **Display:** overlay decoded text on the video feed; show the detected dots/cells for an impressive, debuggable demo view.
- **TTS:** speak completed words/lines, **debounced** so it doesn't repeat the same text every frame.
  - `pyttsx3` — offline, cross-platform, zero-setup → **use for the MVP.**
  - `gTTS` — online, more natural voice → nice-to-have.
  - `Piper` — fast offline neural TTS, good on edge/phone → strong for the "accessibility, works anywhere" story.
- **Accessibility UX:** since the *users are blind/low-vision*, the interface itself must be accessible — large high-contrast text, audio-first feedback, an audible "ready/scanning/done" cue, and keyboard/voice control. This is an explicit judging criterion; spend real effort here, not just on the model.

---

## 4. Data strategy

Data is the bottleneck. Attack it on three fronts.

| Source | What it gives you | Use |
|---|---|---|
| **DSBI** (Double-Sided Braille Image dataset) | Real pages with recto/verso **dot + cell** annotations | Primary academic training set |
| **Angelina Braille Images Dataset** | ~240+ real **camera** photos, varied lighting/perspective | Real-world robustness + test set |
| **DotNeuralNet repo** | Pre-aggregated Angelina + DSBI + natural-scene + Kaggle in **YOLO format**, with **pretrained YOLOv5/YOLOv8 weights** | Huge shortcut — fine-tune from these weights |
| **Kaggle "Braille Character Dataset"** | Single-character `a`–`z` crops | Classifier baseline / augmentation (not detection) |
| **Your own rig images** | Photos from *your exact capture setup* | **Critical** — fine-tune on these; this is the test distribution |
| **Synthetic renderer** | Unlimited perfectly-labeled pages | Pretrain at scale |

### Two techniques that punch above their weight
1. **Synthetic data generation (original work + infinite labels).** Write a small renderer: random English text → Braille Unicode → draw dots at realistic pitch with shadows, noise, slight rotation/perspective, varied lighting. You get unlimited images with *pixel-perfect* dot labels. **Pretrain on synthetic, fine-tune on real.** This directly fixes data scarcity and is great to show in the README.
2. **Collect & label your own pages.** Even **100–300** images from your rig, labeled in **Roboflow** or **LabelMe**, dramatically lift real-world accuracy because they match the test conditions exactly. This is also clearly *original work*.

### Discipline that matters for the "legit accuracy" check
- Hold out a **real test set** (your rig + Angelina "uploaded" subset) that you **never train on**. Report metrics on it honestly.
- Keep the split fixed and documented. Since accuracy is being evaluated by a custom AI tool, you want numbers that hold up — don't tune on the test set, and don't demo only the one page that works.

---

## 5. Recommended stack

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.10+** | |
| Detection | **Ultralytics YOLO26-n** (fallback YOLO11-n) | NMS-free, fast CPU inference; AGPL-3.0 |
| CV / geometry | **OpenCV + NumPy** | CLAHE, perspective warp, grid math |
| Braille decode | **liblouis** (Python bindings) + Unicode map | Grade 1 dict + Grade 2 tables |
| TTS | **pyttsx3** (offline) → Piper / gTTS | offline-first for accessibility |
| Labeling | **Roboflow** or **LabelMe** | export YOLO format |
| UI | OpenCV window for demo; optional **Streamlit/Gradio** or simple web app | accessible, audio-first |
| Edge export | ONNX / OpenVINO / TFLite / CoreML | for real-time / mobile |

---

## 6. Evaluation harness (build this early, not at the end)

Because accuracy is judged by a legit custom tool, treat metrics as a first-class deliverable:

- **Per-cell accuracy** (fraction of cells decoded correctly) — your primary CV metric.
- **Character Error Rate (CER)** and **word accuracy** on decoded text — end-to-end quality.
- **Dot-level precision/recall/mAP** — diagnoses the detector in isolation.
- **Latency / FPS** on your demo machine — the real-time criterion.

Make `evaluate.py` run the full pipeline over your held-out test set and print a table. Run it after every meaningful change so you can see regressions. Put the latest numbers in the README.

---

## 7. Repository & engineering (the AI reviewer will read this)

Your code is reviewed by an AI tool and the README/docs are checked, so structure and clarity score points directly.

```
braillevision/
├── README.md                 # the most important file — see below
├── LICENSE                   # AGPL-3.0 (YOLO dependency)
├── TOOLS.md                  # AI / vibe-coding tools disclosure (required)
├── requirements.txt
├── data/
│   ├── README.md             # dataset sources, licenses, how to download
│   └── braille_dots.yaml     # YOLO data config
├── src/
│   ├── capture.py            # camera loop + frame grabbing
│   ├── preprocess.py         # grayscale, CLAHE, perspective warp
│   ├── detect.py             # YOLO dot detector wrapper
│   ├── grid.py               # deskew, pitch estimate, lattice snap, cell assembly
│   ├── decode.py             # 6-bit -> Unicode -> liblouis text
│   ├── stabilize.py          # temporal voting
│   ├── tts.py                # speech output (debounced)
│   └── app.py                # ties it together; real-time entry point
├── synthetic/
│   └── render.py             # synthetic Braille data generator
├── tests/
│   └── test_grid.py          # deterministic grid/decode unit tests
├── models/                   # trained weights (or release links if large)
├── eval/
│   └── evaluate.py           # metrics on held-out test set
└── docs/
    ├── architecture.md
    └── rig.md                # capture-rig photos + setup
```

**README must contain:** problem statement; architecture diagram; **the capture-rig photo + instructions**; setup/install; how to run the real-time demo; dataset sources + licenses; **evaluation results table**; a link to the **demo video**; AI-tooling disclosure; and limitations. A reviewer (human or AI) should be able to understand and run the project in minutes.

**Engineering hygiene the AI reviewer rewards:** small focused modules (as above), docstrings + type hints, no dead code, meaningful names, the deterministic logic covered by `tests/`, and a clean dependency list. Modular code also lets you swap the detector or decoder without rewrites.

**Required-by-brief checklist:** public GitHub repo ✓ · README ✓ · dataset/project docs ✓ · **AI/vibe-coding tools disclosed** (`TOOLS.md`) ✓ · **original work** (synthetic generator + your own labeled data + your geometry code) ✓ · working demo video ✓.

---

## 8. How the plan maps to the judging criteria

| Criterion | What in this plan earns it |
|---|---|
| **1. Physical Braille recognition accuracy** | Oblique-light rig + CLAHE + dot detector + snap-to-lattice decode; synthetic-pretrain → real-fine-tune; honest held-out eval |
| **2. Real-time performance** | YOLO26-n NMS-free, CPU-optimized; ONNX/OpenVINO export; lightweight preprocessing; FPS reported |
| **3. Technical implementation** | Clean CV↔language separation; geometric decode; tested modular code; liblouis for Grade-2 |
| **4. Robustness in real-world conditions** | Dot-level + lattice approach degrades gracefully; perspective correction; temporal voting; varied-lighting training data; double-sided handling |
| **5. Accessibility & UX** | Offline TTS, audio-first feedback, high-contrast UI, audible state cues, keyboard/voice control |
| **6. Innovation & practical impact** | Synthetic data pipeline; the rig-physics insight; offline/edge deployment for a low-cost, genuinely usable reader |
| **7. Demo & submission quality** | Strong README, debug-overlay demo video, public repo, eval table, tooling disclosure |

---

## 9. Timeline (compress/expand to your hackathon window)

Tuned for ~5 working days. **Commit at the end of every phase — push small, meaningful commits throughout** (the submission's git history and commit timestamps are checked, so a steady trail across the timeline matters; avoid one giant end-of-hack dump).

- **Day 1 — De-risk with an end-to-end spike.** Build the capture rig. Get a webcam loop running. Drop in **DotNeuralNet pretrained YOLOv8 weights**, do a crude left-to-right decode, wire up `pyttsx3`. Goal: *something speaks from a camera by end of day*, however rough. *(commit: working end-to-end skeleton)*
- **Day 2 — Robust dot detection + data.** Stand up CLAHE preprocessing. Build the **synthetic renderer**. Start fine-tuning YOLO26-n on synthetic + DSBI/Angelina. Begin collecting/labeling **your own rig images**. *(commits: preprocessing, synthetic generator, first training run)*
- **Day 3 — Grid reconstruction + decode.** Implement and **unit-test** `grid.py` (deskew, pitch, lattice snap) on synthetic layouts, then real frames. Wire `liblouis` decode (Grade 1 solid; Grade 2 attempted). Build `evaluate.py` and get a first metrics table. *(commits: grid module + tests, decoder, eval harness)*
- **Day 4 — Real-time + robustness + UX.** Add temporal voting and the sharpness gate. Export to ONNX/OpenVINO and tune FPS. Fine-tune on your own labeled data. Build the accessible UI + debug overlay. *(commits: stabilization, export, UI)*
- **Day 5 — Polish + submission.** Finalize README, `TOOLS.md`, LICENSE, dataset docs. Record the **demo video** (real physical Braille, live decode, speech). Run final eval, lock numbers, clean the repo. *(commits: docs, final eval, video link)*

---

## 10. Demo video guidance (judges review the video after the hack)

The OpenAI judges may evaluate primarily from your **video submission**, possibly without running the code — so the video carries the project. Show, on camera and unmistakably:

1. **Real physical Braille** (your embossed page) under the rig — make it obvious it's a real bump-paper, not a screen.
2. The **live camera feed** with the **debug overlay** (detected dots + cell boxes) so robustness is visible.
3. The **decoded text** appearing in real time.
4. The **speech output** playing aloud.
5. A quick **honest accuracy** mention and a hard case (e.g. slightly rotated page) to demonstrate robustness rather than a single cherry-picked frame.

Keep it tight (2–3 min), narrate the pipeline, and end on the accessibility angle (offline, low-cost, usable by a blind user independently).

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Colorless dots invisible** (your image 3) | Oblique lighting rig + CLAHE — the #1 fix |
| **Double-sided pages:** front bumps vs back dents look alike | Use the rig's single-sided light direction (shadows disambiguate); optionally train 2 classes recto/verso; for the demo, use single-sided pages |
| **Motion blur / focus drift** | Sharpness gate + temporal voting; fixed-mount rig |
| **Rare letters / numbers / punctuation low accuracy** | Dot-level approach sidesteps per-class imbalance; synthetic generator can oversample rare patterns |
| **Grade-2 contraction complexity** | Ship Grade-1 first (reliable); Grade-2 via liblouis as scoped stretch |
| **Overfitting to one demo page** ("legit" AI accuracy check) | Fixed held-out real test set; report CER honestly; never tune on test |
| **YOLO26 ecosystem rough edges** | YOLO11-n fallback (officially recommended for stable production) |
| **AGPL-3.0 obligations** | License repo AGPL-3.0, disclose in README/TOOLS.md |

---

## 12. Stretch goals (if ahead of schedule)
- **Grade-2 contracted Braille** end-to-end via liblouis.
- **On-device mobile app** (TFLite/CoreML) — a blind user scanning with their own phone is the strongest impact story.
- **Multi-line / full-page** reading with paragraph reconstruction.
- **Math/Nemeth or other languages** (liblouis supports many tables).
- **Confidence-aware re-scan**: when cell confidence is low, prompt an audible "hold steady" and re-capture.

---

### Reference systems worth studying (don't copy — learn the approach, then build original work)
- **Angelina Braille Reader** (Ovodov) — object detection over cells, robust to perspective; trained on DSBI; *Optical Braille Recognition Using Object Detection Neural Network* (ICCV-W 2021).
- **DotNeuralNet** — lightweight YOLOv5/YOLOv8 dot/char recognition "in the wild," with aggregated datasets and pretrained weights.
- **DSBI** — double-sided dataset + dot-detection evaluation.
- **liblouis** — the standard Braille translation/back-translation library (Grade 1/2, many languages).
