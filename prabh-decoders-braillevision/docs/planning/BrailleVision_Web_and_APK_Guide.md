# BrailleVision — Website vs APK: Decision & Deployment Guide

## The honest recommendation (given your clock)

You have two ways to ship this, and they are not equal in risk:

1. **Live website (Gradio on Hugging Face Spaces) — do this.** It reuses your existing Python almost verbatim, goes public at a URL in well under an hour, and is the foolproof win.
2. **Open that website on your phone** → it uses the **phone camera**. You get the "mobile app" feel — and the phone's better close-up/macro camera, which genuinely helps for reading Braille — with **zero app-build pain**.
3. **Optionally wrap it as an installable app (PWA / PWABuilder)** for a home-screen icon, without writing native code.
4. **Real APK (Flutter)** is a *real* option and not hard *if Flutter is already set up* — but the toolchain + Dart can eat 2–4 hours. Treat it as a **stretch bonus only if you're comfortably ahead**.

**Decision rule:** ship the website first (guaranteed public URL that also works on a phone). Add an APK only if H6 leaves you hours of slack. Keep your Mac `app.py` (or the website) as the always-works demo for the video.

A public **URL a judge can open on their own phone** is, by itself, a strong and very accessible submission.

---

## Path A — Live website (recommended)

Files: **`app_web.py`** (in this kit) + the `requirements.txt` below + your `best.pt`.

`app_web.py` is the same pipeline as `app.py`: webcam stream → YOLO → reading-order decode → annotated view + text, plus a **Speak** button (gTTS audio that auto-plays). The green-box overlay looks great on a demo video.

**requirements.txt** (for the Space — note *headless* OpenCV):
```
gradio
ultralytics
opencv-python-headless
gtts
numpy
```

**Deploy on Hugging Face Spaces (~10–15 min):**
1. huggingface.co → **New Space** → SDK = **Gradio**, hardware = **CPU (free)** — fine for a nano model.
2. Upload three files: **`app.py`** (rename `app_web.py` → `app.py`; Spaces runs `app.py` by default), **`requirements.txt`**, and your **`best.pt`**.
3. It builds and goes live at `https://huggingface.co/spaces/<you>/braillevision`. Share that URL; open it on your phone to use the phone camera.

**Test locally first (instant):**
```bash
pip install gradio ultralytics opencv-python gtts numpy
python app_web.py                       # opens at http://localhost:7860
# or, for an instant temporary public link without HF:
#   change the last line to  demo.launch(share=True)
```

**Notes / gotchas:**
- Use **`opencv-python-headless`** on the server — plain `opencv-python` needs a display and fails on Spaces.
- Free Spaces are **CPU**; a nano model streams at a few FPS — fine for a demo. For more speed, keep `imgsz` small, raise `stream_every`, or request ZeroGPU.
- The Speak button uses **gTTS** (needs internet — Spaces has it). For browser-side offline speech you could swap in the Web Speech API, but the button is the foolproof choice.
- `app_web.py` uses a single shared smoothing buffer (fine while *you* demo). If multiple people open the URL at once, readings can interleave — not a problem for recording your demo.

**Make it installable (optional, ~10 min):** point **PWABuilder** (pwabuilder.com) at your live Space URL — it can produce an installable PWA and even generate an **Android package from the URL**, giving you an installable artifact without native code.

---

## Path B — Real APK (stretch: on-device, best camera, fully offline)

Use the **official Ultralytics YOLO Flutter plugin** (`ultralytics_yolo` / `ultralytics/yolo-flutter-app`). It gives a live camera + detections in a few lines, supports your **custom YOLO26 TFLite** model, and runs on-device (~30 FPS on modern phones) — the strongest accessibility/impact story.

1. **Export your model to TFLite** (Mac or Kaggle):
   ```bash
   yolo export model=models/best.pt format=tflite int8=True imgsz=640
   ```
   (Use the plugin's exact export parameters — it is strict about them; check its README.)
2. **Get the example app:** clone `github.com/ultralytics/yolo-flutter-app` and open the `example/` Flutter app.
3. **Add your model:** drop the `.tflite` (and its metadata `.yaml`) into `example/assets/models/`.
4. **Wire the camera view:**
   ```dart
   YOLOView(
     modelPath: 'assets/models/best_int8.tflite',
     task: YOLOTask.detect,
     onResult: (results) {
       // results: list of { className, confidence, boundingBox }
       // sort by boundingBox x -> concatenate className -> the word
       // speak it with the flutter_tts package
     },
   )
   ```
5. **Decode + speak:** in `onResult`, sort detections left→right, join `className` into a string (your reading-order logic, in Dart), and speak with **`flutter_tts`**.
6. **Build + distribute:**
   ```bash
   flutter build apk --release
   ```
   Host `build/app/outputs/flutter-apk/app-release.apk` on a **GitHub Release** for download. No Play Store needed for a hackathon.

**Reality check:** needs Flutter + Android SDK installed and ~30 min of Dart for the decode/TTS. Worth it **only if** you're ahead of schedule.

---

## License

Both the Gradio-app-with-YOLO and the Flutter plugin are **AGPL-3.0** (Ultralytics dependency). Keep your repo(s) AGPL-3.0 and note it in the README.

---

## Fitting it into your remaining hours

- Slot **Path A** into the **H6–H9** block: once you have trained weights, deploying the Space is ~15 minutes and gives you a public-URL deliverable **and** a phone-camera demo. You can do this alongside the Mac demo, not instead of it.
- Treat **Path B** as a **post-freeze bonus** only if you have hours of slack.
- Record the **video** against whichever is most stable at H9 — web app on a phone, web app on a laptop, or the Mac `app.py`.

## What to put in the README

Link the **live URL** (and the **APK release**, if you built one). Both count as a working demo. Keep everything else from the runbook: rig photo, run steps, held-out accuracy table, TOOLS.md, AGPL license.
