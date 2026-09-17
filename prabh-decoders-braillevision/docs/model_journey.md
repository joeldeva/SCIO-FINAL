# BrailleVision — Model Development Journey

> How we went from a single dataset to a multi-source, transfer-learned Braille detection system in 12 hours.

---

## The Challenge

Detect and decode embossed Braille characters (a–z) from real-world camera images — printed books, handwritten slate-and-stylus pages, and live webcam feeds.

**Approach**: YOLO object detection where each Braille cell is a bounding box classified as a letter (a–z), followed by a reading-order algorithm that reconstructs text line-by-line.

---

## Chapter 1: The Baseline

We started with a single Roboflow dataset (yapayzeka/braille-detection-vxtp1):

| Metric | Value |
|--------|-------|
| Images | 1,324 |
| Bounding boxes | ~21,000 |
| Classes | 26 (A–Z) |

**Problem**: One dataset = one visual style. Would overfit and fail on real-world variety.

---

## Chapter 2: Dataset Engineering

### Data Sources Explored

| Dataset | Source | Images | Usable? | Outcome |
|---------|--------|--------|---------|---------|
| yapayzeka | Roboflow | 1,324 | ✅ | Primary dataset |
| braille-kp | Roboflow | 313 | ❌ | Classification only, no boxes |
| **Angelina Braille** | GitHub | 290 | ✅ | Converted from bitmask CSV |
| augmented-startups/braille-v5 | Roboflow | 12,773 | ❌ | Export unavailable |
| **DotNeuralNet** | GitHub | — | ✅ | Pretrained weights used |

### Angelina Conversion Challenge

The Angelina dataset had a unique format — bitmask integers encoding which Braille dots are present:

```
CSV: 0.082;0.134;0.106;0.163;5
     ↑ normalized box coords  ↑ bitmask: dots 1,3 = 'k'
```

We built `converters/angelina_to_yolo.py` to decode bitmasks → English letters → YOLO format.

### Merged Result

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Images** | 1,324 | **1,614** | +22% |
| **Boxes** | ~21K | **90,469** | **+4.3×** |
| **Input types** | Synthetic | Books + Handwritten + Camera | All requirements covered |

---

## Chapter 3: Three Models, Three Strategies

### 🟢 Model A — "The Safe Bet"

| Setting | Value |
|---------|-------|
| Architecture | YOLOv8n (nano, 3.2M params) |
| Dataset | Merged 1,614 images / 90K boxes |
| Epochs | 100 (patience=30) |
| Augmentation | Mild (5° rotation, mosaic) |
| Strategy | Fast, reliable baseline for live demo |

**Training progress**:
```
Epoch 1: mAP50 = 0.141  (cold start)
Epoch 2: mAP50 = 0.664  (huge jump — transfer learning working)
Epoch 7: mAP50 = 0.830  (already strong, still climbing)
```

---

### 🔵 Model B — "The Heavy Hitter"

| Setting | Value |
|---------|-------|
| Architecture | YOLOv8s (small, 11.2M params) |
| Dataset | Same merged dataset |
| Epochs | 150 |
| Augmentation | Heavy (10° rotation, mixup, copy-paste, perspective warp) |
| Strategy | Push for maximum accuracy with bigger model |

**Risk vs Reward**: 3.5× more parameters may capture finer details but takes longer and risks overfitting.

---

### 🟡 Model C — "The Transfer Learner" (DotNeuralNet)

We discovered [DotNeuralNet](https://github.com/snoop2head/DotNeuralNet) — a YOLOv8 already trained on 64-class Braille dot patterns. Its backbone already knows what embossed dots look like.

```
DotNeuralNet (64 classes)
    │
    ├── BACKBONE (kept) — already knows Braille textures
    │
    └── HEAD (replaced) — retrained for our 26 a-z classes
```

This pretrained model file (`dotneural_pretrained.pt`, 50MB) is bundled with our training dataset for optional warm-start.

---

### 🟡 Model C — "The Latest Generation" (YOLOv11n)

| Setting | Value |
|---------|-------|
| Architecture | YOLOv11n (latest gen nano, 2.6M params) |
| Dataset | Same merged dataset |
| Epochs | 120 |
| Augmentation | Medium (7° rotation, mosaic, light mixup) |
| Strategy | Smallest possible model for mobile/edge deployment |

**Results**:
```
mAP@50:    89.29%
mAP@50-95: 66.92%
Precision: 89.70%
Recall:    86.73%
Model size: 5.2MB
```

**Verdict**: 4× smaller than Model B with only 4% accuracy drop. Perfect for mobile deployment where model size matters.

---

## Chapter 4: Architecture Decision

| Model | Expected mAP50 | Size | Speed | Best for |
|-------|---------------|------|-------|----------|
| A (DotNeuralNet transfer) | 92.88% | 50MB | Fast | Highest precision |
| B (YOLOv8s) | 93.15% | 21MB | Medium | Best overall |
| C (YOLOv11n) | 89.29% | 5.2MB | Fastest | Mobile/edge |

```
                DATA ENGINEERING                    MODEL TRAINING
  ┌─────────────────────────────┐    ┌──────────────────────────────┐
  │ Roboflow (1,324)            │    │ Model A: nano + mild aug     │
  │ + Angelina (290, 69K boxes) │───►│ Model B: small + heavy aug   │
  │ = 1,614 images / 90K boxes  │    │ Model C: YOLOv11n mobile     │
  └─────────────────────────────┘    └─────────────┬────────────────┘
                                                   │
                                     ┌─────────────▼────────────────┐
                                     │ INFERENCE                    │
                                     │  inference.py → photos       │
                                     │  app.py      → live webcam   │
                                     │  app_web.py  → browser/phone │
                                     │  reading_order() → text      │
                                     │  text-to-speech output       │
                                     └──────────────────────────────┘
```

**Winner selection**: Compare mAP@50, then test on our own held-out photos. Ship whichever performs best in real-world conditions.

---

## Credits

| Resource | Author | Usage |
|----------|--------|-------|
| [Angelina Braille Dataset](https://github.com/IlyaOvodov/AngelinaDataset) | Ilya Ovodov | 290 real-world Braille photos |
| [DotNeuralNet](https://github.com/snoop2head/DotNeuralNet) | snoop2head | Pretrained YOLOv8 braille backbone |
| [yapayzeka/braille-detection](https://universe.roboflow.com/yapayzeka/braille-detection-vxtp1) | yapayzeka | 1,324 labeled images |
| [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) | Ultralytics | Detection framework |

---

*Built in 12 hours. Three models. One mission: make Braille readable by AI.*
