# BrailleVision — 12-Hour Execution Runbook

**Mission:** a camera reads real embossed Braille and speaks it, demonstrated in a recorded video, with a public repo + README.

**The one rule that wins this:** a working demo beats a perfect pipeline. The judges score your **video**, not your ambitions. So: **get something reading paper and talking by Hour 2**, then spend the rest making it accurate and recording it. **Freeze all features at Hour 9.** The classic 12-hour death is adding code until the end and breaking the demo with no time to record.

Files in this starter kit: `app.py` (the Mac demo), `train_kaggle.py` (training, both accounts), and the `evaluate.py` below.

---

## 1. Locked scope decisions (decide once, do not reopen)

| Decision | Choice | Why |
|---|---|---|
| Braille grade | **Grade 1 only** | Your samples are uncontracted; skip liblouis/contractions entirely |
| Primary model | **Cell classifier** (box → letter) | It's your existing prototype; decode is just "sort boxes, read labels". Grid-based dot decoding eats hours of debugging |
| Paper | **Single-sided, oblique light** | Build the rig first; it's the cheapest accuracy win and non-negotiable for colorless dots |
| Synthetic data | **Skip** unless a spare person | Real captured data + augmentation is enough in 12h |
| Dot-detector + geometry | **Stretch only** | Touch it only if you're hours ahead |
| Feature freeze | **Hour 9, hard** | Everything after is record + polish + submit |

---

## 2. Roles (merge if fewer than 3 people)

- **APP (Mac):** owns `app.py` — webcam → model → decode → speech → overlay. Gets the crude version live by H2, then polishes.
- **DATA:** builds the rig, captures and labels images, owns the held-out test set. The accuracy bottleneck is data, not model.
- **KAGGLE:** runs `train_kaggle.py` on **both** accounts (A safe / B push), monitors, hands trained weights to APP.

Everyone commits to the shared repo. Communicate via one channel; post each weights hand-off and each blocker immediately.

---

## 3. Setup — Hour 0 to 0.5 (do all of this in the first 30 minutes)

**The light rig (10 minutes, highest ROI of the day).** Mount the camera/phone on a stand pointing straight down at the page. Put a small LED (phone torch / desk lamp) **low and to one side** so light rakes across the paper and every dot casts a shadow. Tape the paper flat at a fixed spot. This single change can move detection from ~50% to ~90%+ on embossed paper. Photograph the rig for the README.

**Mac environment:**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -U ultralytics opencv-python numpy
# macOS TTS uses the built-in `say` command (no install). On other OSes: pip install pyttsx3
```
> macOS will ask for **camera permission** the first time — grant it in System Settings → Privacy & Security → Camera, or you'll get black frames. If `--cam 0` is wrong (e.g. an iPhone hijacks index 0 via Continuity Camera), try `--cam 1`.

**Both Kaggle accounts:** new Notebook → Settings → **Accelerator = GPU**, **Internet = ON**. Keep `train_kaggle.py` open in each.

**Repo (first commit NOW):**
```bash
git init && git remote add origin <your-public-repo>
mkdir -p src models data eval docs
printf "# BrailleVision\nReal-time embossed-Braille reader → text + speech.\n" > README.md
git add . && git commit -m "init: project skeleton" && git push -u origin main
```
Commit timestamps are checked — **start the git trail now** and commit every 1–2 hours with real messages, not one dump at the end.

---

## 4. The two-account strategy

Quota is **not** your bottleneck — a nano model on a few thousand images trains in well under an hour, and each account has ~30 GPU-hrs/week. Use the two accounts for **parallel experiments**, both backed by Kaggle background execution (training continues if you close the tab):

- **Account A — SAFE (`MODEL_VARIANT="A"`):** warm-start from your **existing prototype weights**, fine-tune on captured rig images + any public Braille data. A is therefore *never worse than what you already have*. This is your guaranteed demo model.
- **Account B — PUSH (`MODEL_VARIANT="B"`):** fresh `yolo26s` with heavy augmentation on the same dataset. Goal: beat A on robustness.

At H6 you compare A and B **on your held-out rig photos** and ship the winner. If B loses or breaks, you ship A and lose nothing.

---

## 5. Hour-by-hour timeline (the master schedule)

Each block ends with a **commit** and, where marked, a **GATE** — a go/no-go check with a fallback.

### H0–0.5 · War room
Rig built. Mac env + both Kaggle notebooks ready. Empty repo pushed.
*Commit: `init`.*

### H0.5–2 · Get to a living demo (APP's only job this block)
Wire your **existing prototype weights** into `app.py`:
```bash
python app.py --weights models/your_existing.pt --conf 0.3
```
Point it at the page under the rig. You want letters appearing on screen and speech firing — rough is fine.
- DATA: start capturing 50–150 photos of the page at varied positions/distances/light; begin labeling in Roboflow using **model-assisted labeling** (run the model, correct its guesses — far faster than from scratch).
- KAGGLE: get both notebooks installing + reading the dataset; kick off A as soon as labels exist.

**GATE @ H2 — is it reading paper and speaking?**
- **YES →** proceed to polish.
- **NO →** work the fallback ladder (§7) in order. Do not proceed until *something* reads and speaks, even from a still image.
*Commit: `feat: live webcam demo (baseline weights)`.*

### H2–6 · Make it good
- APP: add temporal voting (already in `app.py`, tune `--vote`), debounced speech, the accessible UI (big high-contrast text + audio "scanning/ready" cues), and the green-box debug overlay (great on video). Add `--clahe` only if your rig images actually need contrast (and then train with the same preprocessing — keep train/infer consistent).
- KAGGLE: A fine-tuning; launch B. Watch `mAP50` in the logs.
- DATA: finish labels; **lock a held-out test set** (10–30 of your rig photos the models never train on) + a `labels.csv` of their true text.
*Commits: `feat: temporal voting`, `feat: accessible UI + overlay`, `data: test set`.*

### H6–9 · Swap in the trained model + measure
- Download `best.pt` from each Kaggle account (Output panel). On the Mac, optionally export for speed:
```bash
yolo export model=models/best.pt format=coreml      # ~2x faster on M2; gives best.mlpackage
python app.py --weights models/best.mlpackage
```
- Run `evaluate.py` (below) on the held-out set for **both** A and B → metrics table.
- **Pick the winner honestly.** Update `models/best.pt`.

**GATE @ H9 — FEATURE FREEZE.** Whatever runs now is the demo. Stop adding things.
*Commits: `model: integrate trained weights`, `eval: held-out metrics`.*

### H9–11 · Record + document
- **Record the demo video** (shot list in §10). Get a clean take of paper → live decode → speech.
- Finalize `README.md`, `TOOLS.md`, `LICENSE` (templates in §9). Put the metrics table and video link in the README.
- Verify the repo runs clean from a fresh clone (`pip install`, `python app.py --weights ...`).
*Commits: `docs: README + TOOLS + LICENSE`, `docs: demo video link`.*

### H11–12 · Buffer + submit
Final commit, push, submit (repo link + README + video). Re-watch the video end to end. **Then stop touching it.**
*Commit: `final: submission`.*

---

## 6. evaluate.py (honest accuracy on your held-out set)

The accuracy check is a legit custom tool, so report real numbers on data you never trained on. Put your test images in `test/` with a `test/labels.csv` of `filename,truth`.

```python
# evaluate.py  ->  python evaluate.py models/best.pt
import csv, sys, cv2
from app import reading_order          # reuse the exact decode the demo uses
from ultralytics import YOLO

def cer(ref, hyp):                     # character error rate = edits / len(ref)
    m, n = len(ref), len(hyp)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ref[i - 1] != hyp[j - 1]))
            prev = cur
    return dp[n] / max(1, m)

model = YOLO(sys.argv[1] if len(sys.argv) > 1 else "models/best.pt")
names = model.names
rows = list(csv.DictReader(open("test/labels.csv")))
tot, exact = 0.0, 0
for r in rows:
    res = model.predict(cv2.imread("test/" + r["filename"]), conf=0.35, verbose=False)[0]
    dets = [((x1 + x2) / 2, (y1 + y2) / 2, names[int(b.cls[0])], y2 - y1)
            for b in res.boxes
            for (x1, y1, x2, y2) in [b.xyxy[0].tolist()]]
    pred = reading_order(dets).replace("\n", " ").strip()
    c = cer(r["truth"].strip(), pred); tot += c
    exact += (pred == r["truth"].strip())
    print(f'{r["filename"]:22s} truth="{r["truth"]}"  pred="{pred}"  CER={c:.2f}')
print(f'\nN={len(rows)}  exact-match={exact/len(rows):.0%}  mean-CER={tot/len(rows):.2f}')
```

Report **exact-match %**, **mean CER**, and the live **FPS** (shown in the demo window). Don't tune on the test set; don't demo only your one lucky page.

---

## 7. The foolproof fallback ladder (read this when stuck)

The whole plan is built so you **always have a working artifact**. At every blocker, drop down one rung — never stall.

**Demo won't show anything (H2 gate):**
1. Lower confidence: `--conf 0.15`.
2. Wrong camera: `--cam 1` (and check macOS camera permission).
3. Improve the **light** before blaming the model — re-angle the LED.
4. Model won't load / bad results → use your **existing prototype weights** (known-good).
5. Live webcam still failing → run detection on a **still photo** instead of the camera (a high-quality shot of the page). A photo-based reader still satisfies "reads physical Braille."
6. Absolute last resort → the video shows reading a **printed Braille photo** held to the camera. Still a valid demo.

**Kaggle gives worse weights than you started with (H6 gate):**
- Keep your current weights. Account A is warm-started from them, so the floor = your starting model. **Never ship worse than you began.**

**App is flaky live (H10):**
- Record reading a **still, well-lit page** or a slow careful pass. A clean recording of a slightly limited demo beats a live crash. The video is what's judged.

**Out of time:**
- Submit what runs at H11 with an honest README. A working Grade-1 single-word reader with a clean video and repo scores across every criterion. An unfinished "ambitious" system scores on none.

---

## 8. Repo structure (matches this kit)

```
braillevision/
├── README.md          # most important file — see template
├── LICENSE            # AGPL-3.0 (YOLO dependency)
├── TOOLS.md           # AI / vibe-coding tools disclosure (REQUIRED by brief)
├── requirements.txt   # ultralytics, opencv-python, numpy
├── app.py             # real-time Mac demo
├── train_kaggle.py    # training (both accounts)
├── evaluate.py        # held-out metrics
├── models/            # best.pt / best.mlpackage (or a release link if large)
├── data/README.md     # dataset sources + licenses + how you captured/labeled
├── test/              # held-out images + labels.csv
└── docs/rig.md        # capture-rig photo + setup
```

---

## 9. Copy-paste templates

**README.md skeleton**
```markdown
# BrailleVision
Real-time reader for physical embossed Braille → English text + speech.

## What it does
Webcam → YOLO cell detector → reading-order decode → on-screen text + spoken output, running offline on a MacBook M2.

## Demo
[2-min video](LINK)   ·   ![rig](docs/rig.jpg)

## Results (held-out set, our capture rig)
| Model | exact-match | mean CER | FPS |
|------|------|------|------|
| A (fine-tuned) | XX% | 0.XX | XX |
| B (yolo26s)    | XX% | 0.XX | XX |

## Run
    pip install -r requirements.txt
    python app.py --weights models/best.pt        # or best.mlpackage on Apple Silicon
    # keys: q quit · s speak · space pause

## How it works
Capture rig (oblique light) → CLAHE (optional) → YOLO detection → reading-order
decode (Grade-1 map) → temporal voting → text + speech. See docs/.

## Data
Sources + licenses in data/README.md. Held-out test set in test/.

## Limitations
Grade-1 (uncontracted) Braille; single-sided pages; tuned for our rig lighting.

## AI tooling
See TOOLS.md.
```

**TOOLS.md** (required — be honest)
```markdown
# AI / vibe-coding tools used
- <tool> — <what for, e.g. scaffolding app.py, debugging the decode>
- <tool> — <e.g. README drafting>
All code reviewed and tested by the team. Pretrained weights / datasets credited in data/README.md.
```

**LICENSE:** use **AGPL-3.0** — Ultralytics YOLO (YOLO26/11/8/5) is AGPL-3.0, so your repo must be compatible. Note this in the README.

**requirements.txt**
```
ultralytics
opencv-python
numpy
```

---

## 10. Demo video shot list (2–3 minutes — this is what judges watch)

Record at H9–11. Keep it tight, narrate the pipeline.

1. **Establish it's real:** the embossed paper under the rig, in hand — make clear it's bump-paper, not a screen.
2. **Live feed + green-box overlay:** dots/cells detected in real time → visible robustness.
3. **Decoded text** appearing on screen.
4. **Speech** playing aloud (turn the volume up; let the `say` output be heard).
5. **One hard case:** a slightly rotated or differently-lit page, to show robustness beyond one lucky frame.
6. **Close on impact:** offline, low-cost, usable by a blind person independently. Mention your held-out accuracy honestly.

If live is flaky, record reading a still well-lit page — a clean take wins over a live crash.

---

## 11. Submission checklist (final 30 minutes)

- [ ] Public GitHub repo, runs from a fresh clone
- [ ] README: what/run/results/limitations + **rig photo** + **video link**
- [ ] **TOOLS.md** present (AI-tool disclosure)
- [ ] **LICENSE** = AGPL-3.0
- [ ] `data/README.md`: dataset sources + licenses
- [ ] Held-out metrics in README (exact-match, CER, FPS)
- [ ] Demo video shows **real paper → live decode → speech**
- [ ] Git history shows steady commits across the 12 hours
- [ ] Submitted (repo + README + video), then **stop**

---

## 12. Judging-criteria coverage

| Criterion | Covered by |
|---|---|
| Physical recognition accuracy | Oblique-light rig + fine-tuned model + honest held-out eval |
| Real-time performance | YOLO nano + CoreML on M2; FPS shown; `--every` frame-skip if needed |
| Technical implementation | Clean modular `app.py`/`train_kaggle.py`/`evaluate.py`; tested decode |
| Robustness | Temporal voting; varied-lighting/position training data; hard-case in demo |
| Accessibility & UX | Offline speech, audio cues, high-contrast text, keyboard control |
| Innovation & impact | The rig-physics insight; offline, low-cost, genuinely usable reader |
| Demo & submission | Strong README, debug-overlay video, public repo, metrics, tooling disclosure |

---

## 13. Mac / OpenCV / YOLO gotchas (don't lose 30 minutes to these)

- **Black frames** → camera permission not granted (System Settings → Privacy → Camera) or wrong `--cam` index.
- **No speech** → on macOS `app.py` uses the built-in `say`; test it: `say "hello"` in Terminal. On other OSes `pip install pyttsx3`.
- **Slow / laggy** → use a **nano** model, export to **CoreML** (`format=coreml`), raise `--every 2`, or lower capture resolution.
- **MPS predict errors** → just run on CPU (a nano model is real-time on the M2 CPU) or use the CoreML model.
- **Kaggle won't pip install** → Internet toggle is OFF in notebook settings.
- **CUDA OOM on Kaggle** → lower `BATCH` to 8 or `IMGSZ` to 640 in `train_kaggle.py`.
- **Train/infer mismatch** → if you `--clahe` at inference, your training images must be preprocessed the same way (or just don't CLAHE if the rig light already gives high contrast).
- **Garbled spaces in output** → tune `--space_mult` (lower = more spaces).

---

**Now:** APP starts the H0.5 spike with your existing weights, DATA builds the rig and starts capturing, KAGGLE gets both notebooks ready. First commit goes up in the next 10 minutes. Go.
