<div align="center">

# 👁️‍🗨️ BrailleVision

### **Seeing Braille. Speaking Words. Empowering Lives.**

*An AI-powered assistive technology that translates physical Braille into readable text and natural speech — in real time.*

<br>

[![mAP@0.5](https://img.shields.io/badge/mAP%400.5-98.0%25-brightgreen?style=for-the-badge&logo=target)]()
[![Inference](https://img.shields.io/badge/Inference-24ms-orange?style=for-the-badge&logo=lightning)]()
[![Model](https://img.shields.io/badge/Model-YOLOv8m-blue?style=for-the-badge&logo=pytorch)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)]()
[![Letters](https://img.shields.io/badge/Coverage-26%2F26%20A--Z-success?style=for-the-badge)]()

<br>

**🏆 BrailleVision Hackathon 2026 Submission**

[**🎬 Watch Demo**](https://drive.google.com/file/d/1XIyiPZLWCgqCx4Z11temPelqa8oo_plR/view?usp=sharing) · [**🚀 Quick Start**](#-quick-start) · [**🧠 Architecture**](#%EF%B8%8F-technical-architecture) · [**📊 Performance**](#-model-performance)

</div>

---

<img width="814" height="606" alt="all_braillie_letter" src="https://github.com/user-attachments/assets/ad36052f-e6a6-4ec4-94cb-25bb7e19d8ae" />


## 🌍 The Problem We're Solving

> **Over 285 million people worldwide are visually impaired** — yet Braille remains locked behind a wall of inaccessibility for the **sighted world around them**. Parents who can't read their child's Braille homework. Teachers without certification. Friends, doctors, employers — all unable to bridge the gap.

**BrailleVision tears down that wall.**

Point a phone camera at any Braille text. In **24 milliseconds**, our AI reads it back to you — as text, as speech, as a visual dot pattern. No special hardware. No training. Just instant, universal access to a writing system that has been isolated for over 200 years.

<div align="center">

| 🎯 The Challenge | ⚡ Our Solution |
|:---|:---|
| Braille is invisible to anyone who hasn't learned it | One-shot computer vision — **98.0% accuracy** across all 26 letters |
| Existing OCR tools fail on embossed, low-contrast dots | Specialized YOLOv8m fine-tuned on **2,062 real-world Braille images** |
| Multi-word lines are often merged into nonsense | Spatial **row + word segmentation** algorithm correctly parses `Cat Dog Mouse` |
| Slow, cloud-bound APIs aren't accessible | **Runs locally** at 24 ms/image on a single GPU |

</div>

---

## ✨ What Makes BrailleVision Different

<table>
<tr>
<td width="50%" valign="top">

### 🚀 **Real-Time AI**
Sub-25 ms inference per frame on GPU. Point your webcam at Braille and watch words appear *as you move*.

### 🧭 **Smart Spatial Parsing**
Our **dual-axis segmentation** correctly separates words within the same row (`Cat | Dog | Mouse`) — not just rows. This is the algorithmic edge most Braille OCRs miss.

### 🛡️ **Robust 5-Pass Cascade**
For tough images, we run multi-scale + TTA + ROI + tiled + CLAHE-enhanced inference, all merged through **class-aware NMS**. No detection is left behind.

</td>
<td width="50%" valign="top">

### 🎨 **Accessible-First UI**
Animated Braille-dot visualizer · keyboard-navigable tabs · ARIA labels · reduced-motion support · screen-reader announcements.

### 🔊 **Natural Speech**
Multi-word: full sentence at natural pace. Single word: spelled letter-by-letter for clarity. Powered by the browser's Web Speech API — works offline, no API keys.

### 🎓 **Research-Grade Training**
Two-phase transfer learning. Drive-backed Colab pipeline that survives disconnects. Auto-resume. Per-class AP analysis. **All in 3.6 hours of training.**

</td>
</tr>
</table>

---

## 🎬 See It In Action

```
📷 Physical Braille            🧠 BrailleVision              🔊 Output
─────────────────              ──────────────                ──────────
⠉⠁⠞   ⠙⠕⠛   ⠍⠕⠥⠎⠑     →     "cat dog mouse"      →     🗣️ "cat dog mouse"
⠃⠗⠁⠊⠇⠇⠑                      "braille"                    🗣️ "braille"
```

> **The bug we fixed:** Older versions read the top row as `atogmouse` — a single blob of merged letters. Our new horizontal-gap algorithm now correctly produces `cat dog mouse`. ✅

---

## 🧭 Workflow at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   1️⃣  INPUT                                                           │
│        ├─ 📷 Live camera (webcam, sampled every 600 ms)              │
│        └─ 🖼️  Image upload (JPG / PNG / WEBP — up to 10 MB)           │
│                                ▼                                     │
│   2️⃣  PREPROCESSING                                                   │
│        ├─ OpenCV decode → BGR numpy array                            │
│        └─ ✨ (Optional) CLAHE + Unsharp + Gamma  ← Enhance & Retry    │
│                                ▼                                     │
│   3️⃣  DETECTION    [YOLOv8m fine-tuned, 26 classes A–Z]               │
│        ├─ conf ≥ 0.25                                                │
│        ├─ IoU  ≥ 0.35                                                │
│        └─ Returns bboxes + labels + confidences                      │
│                                ▼                                     │
│   4️⃣  SPATIAL POST-PROCESSING       ⭐ Core innovation                │
│        ├─ Row clustering    (vertical gaps, ratio 0.55)              │
│        └─ Word segmentation (horizontal gaps, ratio 1.75)            │
│                                ▼                                     │
│   5️⃣  TEXT ASSEMBLY                                                   │
│        └─ Labels → readable string (handles capital/number tokens)   │
│                                ▼                                     │
│   6️⃣  OUTPUT — Quadruple modality                                     │
│        ├─ 📝 JSON  (text, letters, confidence, inference_ms)          │
│        ├─ 🖼️  Annotated image (bounding boxes, conf-coloured)         │
│        ├─ ⠿  Braille dot visualizer (animated grid)                  │
│        └─ 🔊 Speech (Web Speech API / pyttsx3)                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Model Pipeline — Transfer Learning Done Right

Reaching **98% mAP** in just **3.6 hours** isn't luck — it's a deliberate **three-stage transfer learning chain**:

```
   Stage 1                       Stage 2                       Stage 3
┌────────────┐  DotNeuralNet  ┌──────────────────┐  Phase 1  ┌─────────────────┐
│ yolov8m.pt │────training───▶│ yolov8_braille.pt│──heavy───▶│ phase1/best.pt  │
│  (COCO)    │   on Braille   │  (Braille-aware) │   aug     │ mAP@0.5 = 0.978 │
└────────────┘                └──────────────────┘ 120 ep    └─────────────────┘
                                                                      │
                                                                      │ Phase 2
                                                                      │ fine-tune
                                                                      │ (LR ÷10)
                                                                      ▼
                                                          ┌─────────────────────┐
                                                          │  phase2/best.pt 🏆  │
                                                          │  mAP@0.5 = 0.980    │
                                                          │  ← PRODUCTION MODEL │
                                                          └─────────────────────┘
```

### 🔬 Why Two Phases? The Engineering Story

<table>
<tr>
<th width="50%">🌪️ Phase 1 — Exploration</th>
<th width="50%">🎯 Phase 2 — Refinement</th>
</tr>
<tr>
<td valign="top">

**Goal:** Learn robust, augmentation-invariant dot features.

| Parameter | Value |
|---|---|
| Epochs | 120 |
| Optimizer | AdamW, cosine decay |
| Learning rate | `5e-4` |
| Mosaic | 1.0 |
| Mixup | 0.15 |
| Copy-Paste | 0.15 |
| Random Erasing | 0.3 |
| `flipud` | **0.0** ⚠️ |
| Patience | 50 |

⚠️ **`flipud = 0` is critical** — Braille's dot pattern is *vertically asymmetric*. Flipping upside-down corrupts the entire alphabet.

🏁 **Result: mAP@0.5 = 0.978**

</td>
<td valign="top">

**Goal:** Cleanly converge on the true data distribution.

| Parameter | Value |
|---|---|
| Epochs | 40 |
| Optimizer | AdamW, cosine decay |
| Learning rate | `5e-5` (10× lower) |
| Mosaic | 0.0 |
| Mixup | 0.0 |
| Copy-Paste | 0.0 |
| Random Erasing | 0.1 |
| `flipud` | 0.0 |
| Patience | 20 |

💡 Heavy augmentation injects gradient noise. Phase 2 removes that noise, letting the model settle into a tighter optimum.

🏆 **Result: mAP@0.5 = 0.980** (+0.2%)

</td>
</tr>
</table>

### 🏗️ Architecture Specs

| Property | Value |
|---|---|
| Backbone | **YOLOv8m** (medium) |
| Parameters | 25.8 M |
| GFLOPs | 79.1 |
| Fused layers | 93 |
| Output classes | 26 (A–Z) |
| Inference size | 640 × 640 (recommended) |
| Export formats | PyTorch `.pt` + ONNX (dynamic + simplified) |

---

## 🔍 Detection & Translation Logic — The Algorithmic Edge

This is **the core technical contribution** of BrailleVision: turning a bag of bounding boxes into properly punctuated, multi-word English.

### 🧱 Step 1 — YOLO Inference
Each frame is passed through the fine-tuned YOLOv8m. Per detected Braille cell we get:
- Bounding box `(x1, y1, x2, y2)`
- Class label (`a` … `z`)
- Confidence score `[0.0 – 1.0]`

### 📏 Step 2 — Row Clustering *(Top → Bottom)*

Detections are sorted by vertical centre (`cy`). A new row starts whenever the gap exceeds an **adaptive, scale-invariant threshold**:

```python
row_split_gap = max(15.0, median(box_heights) × 0.55)
```

This works at **any resolution** — close-set classroom Braille and widely-spaced book Braille both parse correctly.

### ⭐ Step 3 — Word Segmentation *(Left → Right)* — Our Key Innovation

> **The problem:** Old version read the top row of a `Cat | Dog | Mouse` image as `atogmouse` — one giant merged word.
>
> **The fix:** Within each row, we compute horizontal gaps between consecutive cells and split where the gap exceeds a **multi-criteria adaptive threshold**:

```python
word_gap_threshold = max(
    12.0,                                       # absolute floor
    median(cell_widths)        × 1.75,          # 1.75× a Braille cell width
    median(inter_cell_gaps)    × 1.75,          # 1.75× normal letter spacing
    median(inter_centre_gaps)  × 0.9            # tolerant to misaligned boxes
)
```

Any gap > threshold = **word boundary**. Result: `cat dog mouse` ✅

This is **data-driven** (not hard-coded pixel values), which means it works at any zoom level, any image resolution, and any Braille font size.

### 🔤 Step 4 — Label-to-Text Assembly

The ordered sequence is converted to text with full support for Braille semantic tokens:

| Token | Effect |
|---|---|
| `capital`, `caps` | Next character is uppercased |
| `number`, `#` | Following `a–j` mapped to `1–0` until reset |
| `space`, ` ` | Explicit word separator |

### 🛡️ Step 5 — Robust 5-Pass Cascade *(Batch Inference)*

For challenging real-world images, `inference/predict.py` runs a sophisticated cascade:

| Pass | Strategy | When It Helps |
|---|---|---|
| **1** | Full image @ 640 px | Normal cases |
| **2** | Larger adaptive scale + **TTA** | Small / distant Braille |
| **3** | **Auto-ROI crop** if Braille fills < 55 % of frame | Document photos with whitespace |
| **4** | **Tiled inference** for images ≥ 1280 px | High-resolution scans |
| **5** | **CLAHE-enhanced** pass at low conf | Low-contrast / embossed |

All passes are merged through a **class-aware NMS** that uses both IoU *and* centre-distance normalized by box width — preventing stacked misclassifications like `A/L/L` on the same cell.

### 🚨 Step 6 — Gap Detector *(Quality Signal)*

We compute the median cell-step `(width + inter-gap)` per row. Any actual gap > `1.8 × step` is flagged as a **missing cell** and drawn as a dashed grey `?` box in the annotated output — giving the user (and the judges) instant visibility into model recall.

---

## 📤 Output Generation — Four Modalities

BrailleVision delivers results in **four complementary formats** so that no one is left out:

<table>
<tr>
<td width="25%" align="center">

### 📝
**Detected Text**

Plain UTF-8 string with proper word boundaries.

`"cat dog mouse braille"`

</td>
<td width="25%" align="center">

### 🖼️
**Annotated Image**

Base64 JPEG with conf-coloured boxes (🟢 ≥ 0.75 / 🟡 ≥ 0.5 / 🔴 < 0.5) and missing-cell flags.

</td>
<td width="25%" align="center">

### ⠿
**Dot Visualizer**

Animated 2×3 HTML/CSS grids — sighted users can verify each cell visually.

</td>
<td width="25%" align="center">

### 🔊
**Speech**

Multi-word → natural sentence.
Single word → spelled letter-by-letter.

</td>
</tr>
</table>

### 📋 Example JSON Response

```json
{
  "success": true,
  "text": "cat dog mouse braille",
  "letters": [
    {"letter": "C", "confidence": 93.0},
    {"letter": "A", "confidence": 86.0},
    {"letter": "T", "confidence": 88.0},
    {"letter": "D", "confidence": 91.0}
  ],
  "count": 21,
  "inference_ms": 24.2,
  "image_b64": "..."
}
```

---

## 🏗️ Technical Architecture

A **clean three-layer system** with strong separation of concerns — easy to reason about, easy to extend.

```
┌──────────────────────────────────────────────────────────────────────┐
│  🎨  FRONTEND  —  Vanilla JS + HTML + CSS                            │
│  ─────────────────────────────────────────────────────────────────── │
│  • Drag-&-drop upload zone with live thumbnail                       │
│  • Live camera capture (getUserMedia + canvas)                       │
│  • Animated Braille dot visualizer (CSS grid)                        │
│  • Web Speech API for TTS  +  Web Audio API for waveform             │
│  • History strip, copy-to-clipboard, keyboard navigation, ARIA       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │  HTTP (multipart/form-data)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ⚡  BACKEND  —  FastAPI + Uvicorn                                    │
│  ─────────────────────────────────────────────────────────────────── │
│  • GET   /                  → serves index.html                      │
│  • GET   /health            → model-loaded liveness check            │
│  • POST  /predict           → standard detection                     │
│  • POST  /predict/enhanced  → CLAHE + sharpen + gamma + retry        │
│  • POST  /predict_frame     → lightweight live-camera endpoint       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │  Python function call
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  🧠  INFERENCE CORE  —  app.py + inference/predict.py                │
│  ─────────────────────────────────────────────────────────────────── │
│  • BrailleDetector  (Ultralytics YOLOv8 wrapper)                     │
│      ├─ sort_detections_reading_order()  ← row clustering            │
│      ├─ split_row_into_words()           ← word segmentation         │
│      └─ labels_to_text()                 ← text assembly             │
│  • Robust 5-pass cascade  (predict.py)                               │
│  • Class-aware NMS (IoU + centre-distance)                           │
│  • Auto-ROI + Tiled inference for large images                       │
│  • Gap detector — flags missing cells with dashed boxes              │
└──────────────────────────────────────────────────────────────────────┘
```

### 📦 Module Responsibilities

| File | Role |
|---|---|
| `app.py` | Inference core — `BrailleDetector`, row/word logic, text assembly, CLI modes |
| `main.py` | FastAPI server — REST endpoints, image decoding, enhanced preprocessing |
| `inference/predict.py` | Batch / eval tool — 5-pass cascade, NMS, gap detection, JSON export |
| `static/index.html` | Single-file frontend — UI, camera, dot visualizer, TTS |
| `train.py` | Two-phase YOLOv8 trainer (v4) — Drive backup, resume, ONNX export |
| `model/best.pt` | Fine-tuned production weights (52.1 MB) |
| `model/best.onnx` | ONNX export (99.1 MB) for CPU deployment |

### 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🎯 **Object Detection** | YOLOv8m (Ultralytics 8.4.58) |
| 🔥 **Training Framework** | PyTorch + CUDA 12.8 |
| 👁️ **Computer Vision** | OpenCV |
| ⚡ **Web Backend** | FastAPI + Uvicorn |
| 🎨 **Frontend** | HTML / CSS / Vanilla JavaScript |
| 🔊 **Text-to-Speech** | Web Speech API (browser) · `pyttsx3` (CLI) |
| ☁️ **Training Platform** | Google Colab (Tesla T4 16 GB) |
| 🗂️ **Dataset** | Roboflow Universe (`braillify`, 2,062 images) |
| 📦 **Model Export** | ONNX (dynamic, simplified) |

---

## 📊 Model Performance

### 🏆 Final Production Model (Phase 2)

<div align="center">

| Metric | Score | Industry Reference |
|:---|:---:|:---|
| **mAP@0.5** | **0.980** | ≥ 0.90 considered production-grade |
| mAP@0.5:0.95 | 0.771 | ≥ 0.50 considered strong |
| Precision | 0.943 | ≥ 0.90 considered excellent |
| Recall | 0.976 | ≥ 0.90 considered excellent |
| **Inference Speed** | **~24 ms / image** | ≤ 33 ms = real-time (30 FPS) |
| Total Training Time | 3.6 hrs | On a single Tesla T4 |

</div>

### 📈 Phase Comparison

| Phase | mAP@0.5 | mAP@0.5:0.95 | Epochs | Duration |
|---|:---:|:---:|:---:|:---:|
| Phase 1 (heavy aug) | 0.978 | 0.756 | 120 | 2.6 hrs |
| **Phase 2 (fine-tune)** | **0.980** ▲ | **0.771** ▲ | 40 | 1.0 hr |

### 🔤 Per-Class AP@0.5 (Final Model)

<div align="center">

| Letter | AP | Letter | AP | Letter | AP | Letter | AP |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **A** | 0.971 ✅ | **H** | 0.990 ✅ | **O** | 0.992 ✅ | **V** | 0.992 ✅ |
| **B** | 0.967 ✅ | **I** | 0.990 ✅ | **P** | 0.990 ✅ | **W** | 0.988 ✅ |
| **C** | 0.993 ✅ | **J** | 0.885 ⚠️ | **Q** | 0.995 ✅ | **X** | 0.970 ✅ |
| **D** | 0.987 ✅ | **K** | 0.968 ✅ | **R** | 0.986 ✅ | **Y** | 0.961 ✅ |
| **E** | 0.993 ✅ | **L** | 0.983 ✅ | **S** | 0.991 ✅ | **Z** | 0.995 ✅ |
| **F** | 0.941 ⚠️ | **M** | 0.978 ✅ | **T** | 0.986 ✅ | | |
| **G** | 0.995 ✅ | **N** | 0.991 ✅ | **U** | 0.995 ✅ | | |

</div>

⚠️ **`J` and `F`** have slightly lower AP due to fewer training samples in the dataset — every other letter exceeds 0.94. *(A known and quantified limitation, surfaced through our automated weak-class analyzer in `train.py`.)*

---

## 🗃️ Dataset

| Property | Details |
|---|---|
| 🏷️ **Name** | braillify |
| 🌐 **Source** | Roboflow Universe |
| 🔗 **Link** | https://universe.roboflow.com/nicco-van-hamja-b1vxy/braillify |
| 📸 **Total Images** | 2,062 real, physical Braille photos |
| 🔤 **Classes** | 26 (A – Z) |
| 📐 **Format** | YOLOv8 PyTorch (bounding-box annotations) |
| ✂️ **Splits** | Train 1,757 · Val 206 · Test (separate) |

> Real-world photographs — not synthetic renderings — ensure the model generalizes to actual physical Braille under varied lighting, materials, and angles.

---

## 📂 Repository Structure

```
braillevision/
│
├── 🐍 app.py                       # Inference core: detector + row/word logic + CLI
├── 🌐 main.py                      # FastAPI backend
├── 📋 requirements.txt
├── 📖 README.md                    # ← You are here
│
├── 🎨 static/
│   └── index.html                  # Single-file frontend (UI + JS)
│
├── 🧠 model/
│   ├── yolov8_braille.pt           # DotNeuralNet base weights
│   ├── best.pt                     # Fine-tuned production model (52.1 MB)
│   └── best.onnx                   # ONNX export (99.1 MB)
│
├── 🏋️ training/
│   ├── train.py                    # Two-phase trainer (v4)
│   └── results/
│       ├── phase1/                 # 120-epoch heavy-aug results
│       └── phase2/                 # 40-epoch fine-tune — FINAL
│
├── 🗂️ dataset/
│   ├── data.yaml                   # 26 classes A–Z
│   ├── train/                      # 1,757 images
│   ├── valid/                      # 206 images
│   └── test/
│
├── 🔬 inference/
│   └── predict.py                  # Batch eval + 5-pass robust cascade
│
├── 🖼️ sample_inputs/                # Sample Braille images for judges
├── ✅ sample_outputs/               # Annotated outputs + results.json
│
└── 🎬 demo/
    └── demo_video_link.txt
```

---

## 🚀 Quick Start

### 📦 Install (under 30 seconds)

```bash
git clone <repo-url> braillevision
cd braillevision
pip install -r requirements.txt
```

### 🌐 Option 1 — Web App *(Recommended for Demo)*

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

→ Open **http://localhost:8000** and drag in a Braille image. **Done.**

### 📷 Option 2 — Real-Time Camera (CLI)

```bash
python app.py
```

| Key | Action |
|:---:|:---|
| `s` | Speak current detection |
| `r` | Reset history |
| `q` | Quit |

### 🖼️ Option 3 — Single Image

```bash
# With speech
python app.py --source sample_inputs/test1.jpg

# Headless (e.g. Codespaces)
python app.py --source sample_inputs/test1.jpg --no-speech
```

### 🧪 Option 4 — Batch Evaluation *(for judges)*

```bash
# Process every sample image with full annotation
python inference/predict.py --source sample_inputs/

# Export detailed per-image JSON
python inference/predict.py --source sample_inputs/ --export-json

# Use ONNX for faster CPU inference
python inference/predict.py --source sample_inputs/ --weights model/best.onnx
```

### ⚙️ CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--source` | webcam 0 | Image / video path or webcam index |
| `--weights` | `model/best.pt` | Path to model weights |
| `--conf` | `0.25` | Detection confidence threshold |
| `--iou` | `0.35` | NMS IoU threshold |
| `--no-speech` | `False` | Disable text-to-speech |
| `--debug` | `False` | Print detected labels + row groupings |

---

## 🌐 FastAPI Endpoints

| Endpoint | Method | Description | Purpose |
|---|:---:|---|---|
| `/` | GET | Serves the web UI | Landing page |
| `/health` | GET | Model / liveness check | Monitoring |
| `/predict` | POST | Standard image detection | Default upload path |
| `/predict/enhanced` | POST | CLAHE + sharpen + retry | Low-contrast / embossed |
| `/predict_frame` | POST | Lightweight live-camera endpoint | Webcam streaming |

---

## ♿ Accessibility Commitments

Building accessibility tech demands accessible *tools*. We took it seriously:

- ✅ **WCAG 2.1 AA contrast** — every text/background pair tested
- ✅ **Keyboard navigation** — every interaction reachable via Tab + Enter + Arrow keys
- ✅ **ARIA labels** on every interactive element (`aria-live`, `aria-selected`, `role`)
- ✅ **Screen-reader friendly** — `aria-live="polite"` regions announce detections
- ✅ **Reduced-motion support** — respects `prefers-reduced-motion`
- ✅ **Visible focus indicators** — clear `:focus-visible` outlines
- ✅ **Semantic HTML** — proper headings, landmarks, button elements

---

## 🎓 Training Script Highlights (`train.py` v4)

Lessons learned from 3.6 hours of GPU time, baked into the trainer:

| Feature | Why It Matters |
|---|---|
| ☁️ **Google Drive auto-backup** every 10 epochs | Survives Colab disconnects |
| 🔄 **`--resume` flag** | Restores from Drive if local files lost |
| 📝 **Clean one-line-per-epoch logging** | Browser doesn't crash from log spam |
| 🔬 **Per-class AP analyzer** | Auto-flags weak letters for next iteration |
| 📐 **Multi-size eval (640 & 800)** | Recommends best inference resolution |
| 📦 **Auto-ONNX export** | One command from training to deployment |
| 📊 **JSON + TXT training report** | Auditable, reproducible runs |

---

## 📜 References & Credits

| Resource | Link |
|---|---|
| 🧠 DotNeuralNet (base weights) | https://github.com/snoop2head/DotNeuralNet |
| 🗂️ braillify dataset (Roboflow) | https://universe.roboflow.com/nicco-van-hamja-b1vxy/braillify |
| 🎯 Ultralytics YOLOv8 | https://github.com/ultralytics/ultralytics |
| ⚡ FastAPI | https://fastapi.tiangolo.com |
| 🔊 Web Speech API | https://developer.mozilla.org/docs/Web/API/Web_Speech_API |

---

## 🤝 AI Tools Disclosure

- **Claude (Anthropic)** — project guidance, code architecture, training pipeline design
- **DotNeuralNet** — pretrained `yolov8_braille.pt` used as Stage-2 transfer base
- **Roboflow** — dataset hosting + YOLOv8 format export
- **Google Colab** — Tesla T4 GPU for training

---



## 🌟 The Vision Forward

BrailleVision today reads **English Grade-1 Braille**. The architecture is built to grow:

- 🌐 **Multi-language Braille** — Spanish, French, Arabic, Hindi (datasets already public)
- 📖 **Grade-2 contractions** — full literary Braille support
- 📱 **Mobile-first PWA** — install on any phone, works offline
- 🎧 **Continuous listening mode** — read entire books page-by-page
- 🧑‍🏫 **Learning mode** — teach Braille interactively to sighted family members

Every line of code we wrote was guided by one question: *"Would this help a parent read their child's homework tonight?"*

That question still drives us.

---

<div align="center">

### 👁️‍🗨️ **BrailleVision**

*Making Braille accessible through AI*

**mAP 98.0% · All 26 letters detected · 24 ms inference · Built in 3.6 GPU-hours**

<br>

**Built with ❤️ for the BrailleVision Hackathon 2026**

</div>
