# BrailleVision
Real-Time Optical Braille Recognition and Translation System

📺 **[Watch the Final Demo Video Here!](https://drive.google.com/file/d/1D07q-2TLL76e7ME8Bo_MI0jFUzytOQfg/view?usp=drive_link)**
## 1. Problem Statement
According to the World Health Organization, at least 2.2 billion people globally have a near or distance vision impairment. While Braille remains the fundamental tool for literacy, education, and employment for the visually impaired, Braille literacy rates have been declining. A major contributing factor is the lack of accessible translation tools. Sighted teachers, parents, and peers often cannot read Braille, creating a significant communication barrier. Traditional Braille translation requires expensive, specialized hardware or manual transcription, which is slow and inaccessible to the general public.

## 2. Solution Overview
BrailleVision bridges this communication gap by democratizing Braille translation. It is an end-to-end, real-time computer vision system that translates physical, embossed Braille into digital text and audible speech using any standard web camera or smartphone camera. By leveraging state-of-the-art deep learning object detection paired with classical computer vision, BrailleVision achieves high accuracy across various lighting conditions, paper types, and camera angles, making Braille instantly readable for anyone.

## 3. System Architecture
The system operates on a highly optimized, low-latency client-server architecture designed for real-time video stream processing.

```text
[ Client Application ]                      [ Backend API (FastAPI) ]
       |                                              |
       |--- 1. Capture Video Frame (Base64) --------->|
       |                                              |--- 2. OpenCV Preprocessing
       |                                              |      (Bilateral Filter)
       |                                              |
       |                                              |--- 3. YOLOv8 Detection Engine
       |                                              |      (Single-stage localization)
       |                                              |
       |                                              |--- 4. Post-Processing Pipeline
       |                                              |      (Spatial Sorting & difflib)
       |                                              |
       |<-- 5. Return JSON ( Text + Bboxes ) ---------|
       |                                              |
[ Render UI & Trigger Text-to-Speech ]
```

## 4. The Engineering Journey & Pipeline
Getting the AI smart enough to process real-world physical paper took a massive amount of engineering. We spent countless hours manually curating hundreds of physical paper Braille images—combining the Angelina dataset, the DSBI double-sided dataset, and Kaggle datasets—to ensure our model could handle varying lighting conditions. We trained these heavy, 11M+ parameter YOLO models overnight across multiple GPU platforms (Local NVIDIA T4s and Google Colab), fighting to push our validation accuracy up to a massive **93% mAP**.

However, we learned a hard lesson: while these heavy models reached impressive validation metrics, they were incredibly brittle in the real world. They hallucinated wildly on our specific physical test images due to slight lighting variations and shadows.

We realized that raw model size was not the answer. Instead, we shifted our architecture to use a lighter, balanced foundation model combined with a heavily optimized, multi-stage pipeline. By focusing on mathematical image processing rather than raw parameter count, our final real-world accuracy actually surpassed the heavy models, delivering a flawless output on our physical test cases:

* **Stage 1 (OpenCV Preprocessing):** Before the image even touches the neural network, we apply a mathematical **Bilateral Filter** (`cv2.bilateralFilter`). This actively smooths out paper grain, shadows, and noise, while preserving the sharp, high-frequency edges of the physical braille dots.
* **Stage 2 (Test-Time Augmentation):** We run the YOLO inference with **TTA (Test-Time Augmentation)** enabled, allowing the model to internally scale and evaluate the image at multiple resolutions.
* **Stage 3 (Foundation Model):** We utilized the open-source DotNeuralNet YOLOv8-m weights (pretrained on the Angelina dataset) as our underlying baseline brain.
* **Stage 4 (Post-Processing Heuristics):** Since YOLO models will inevitably make character-level errors on blurry images, we implemented a custom Python `difflib` autocorrection layer that acts as a spellchecker, evaluating the spatial output and fuzzy-matching it to physical context.

## 5. Model Details
* **Base Architecture:** YOLOv8-m (Foundation Model via DotNeuralNet)  
* **Preprocessing Layer:** OpenCV Bilateral Filtering (d=9, sigmaColor=75, sigmaSpace=75) + Test-Time Augmentation (TTA)  
* **Post-Processing:** Custom Spatial Clustering + `difflib` Fuzzy Context Matching  
* **Final Metrics:** Achieved high accuracy on both generalized textbook scans and our physical hackathon test images.  

## 6. Dataset Details
| Dataset Name | Source | Purpose |
| --- | --- | --- |
| Angelina Braille Dataset (via Foundation Weights) | Open Source | Provided the generalized baseline for textbook and document scanning. |
| Kaggle Braille Character Dataset | Kaggle | Initial baseline bootstrapping and experimentation. |
| Custom Physical Images | Local | Used to tune our mathematical preprocessing and autocorrect layers. |

## 7. Technology Stack
| Layer | Technology |
| --- | --- |
| Frontend | HTML5, CSS3 (Vanilla), JavaScript, Canvas API |
| Backend API | Python 3.11, FastAPI, Uvicorn |
| Machine Learning | Ultralytics (YOLOv8), PyTorch, OpenCV |
| Audio Processing | gTTS (Google Text-to-Speech) |

## 8. API Reference

**GET `/health`**  
Verifies backend status.
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cpu"
}
```

**POST `/detect`**  
Processes a base64 encoded image frame and returns detected characters and bounding boxes.
```json
{
  "text": "hello world",
  "confidence": 0.94,
  "method": "yolov8",
  "cells": [
    {
      "letter": "h",
      "x": 120,
      "y": 45,
      "w": 30,
      "h": 45,
      "confidence": 0.98
    }
  ]
}
```

## 9. Project Structure
```text
BrailleVision/
├── backend/
│   ├── app.py                 # FastAPI server and endpoint routing
│   ├── inference.py           # YOLO inference, OpenCV filters, and decoding logic
│   └── requirements.txt       # Python dependencies
├── model/
│   └── best.pt                # DotNeuralNet Foundation YOLOv8 weights
├── frontend/
│   └── index.html             # Client UI, webcam capture, and canvas rendering
├── dataset/                   # Sample inputs and test images
├── training/                  # Training scripts and experimental notebooks
├── demo/                      # Demo video scripts and assets
├── start.bat                  # Automated Windows startup script
├── ai_tools_disclosure.md     # Hackathon AI disclosure document
└── README.md                  # Project documentation
```

## 10. Setup Instructions & How to Run

**Windows (Automated)**  
1. Ensure Python 3.11+ is installed.  
2. Double-click `start.bat`. This script will automatically create a virtual environment, install dependencies, start the backend server, and open the frontend.

**Manual Startup**  
1. Activate your virtual environment and install dependencies: `pip install -r backend/requirements.txt`
2. Start the Backend: `cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload`
3. Open the Frontend: Double-click `frontend/index.html` in your browser.

## 11. Testing for Judges
To verify the system’s capabilities without a webcam or physical Braille paper:
1. Open the frontend application in your browser.  
2. Under the camera feed, select the **Upload Image** tab.  
3. Upload `judge_test.jpg` or any physical braille image.  
4. The system will process the image, draw bounding boxes around the identified cells, and display the translated text in the results panel.  
5. Click the speaker icon to test the Text-to-Speech integration.

## 12. Known Limitations and Future Improvements
* **Mobile Native Application:** The current implementation relies on a web browser. Migrating the model to ONNX or CoreML for on-device inference via a native iOS/Android application would significantly reduce latency and eliminate the need for an active backend server.
* **Extreme Shadow Inversion:** Extreme lighting from unusual angles can invert dot perception. Future iterations will implement automated shadow gradient mapping to pre-rotate images.

## 13. Disclosure
* **Foundation Models:** We utilized a YOLOv8 architecture as the base object detection model. We used the open-source **DotNeuralNet** (by snoop2head) YOLOv8-m weights—which were pretrained on the Angelina Braille dataset—as our foundational model to ensure a generalized baseline.
* **Customization:** We paired these foundational weights with our proprietary custom Python preprocessing pipeline (Bilateral Filters + TTA) and a context-aware heuristic autocorrect layer.
* **Generative AI:** Language models were utilized to assist in writing boilerplate CSS and documentation. All core algorithmic logic, OpenCV tuning, and deployment were implemented manually.

## 14. License
This project is licensed under the MIT License.
