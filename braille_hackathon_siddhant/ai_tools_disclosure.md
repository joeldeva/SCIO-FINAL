# AI Tools Disclosure

As per the BrailleVision Hackathon 2026 rules, we are disclosing the use of Artificial Intelligence tools during the development of this project.

### Tools Used
1. **Ultralytics YOLOv8 & DotNeuralNet Weights**
   - **Purpose:** We utilized a YOLOv8 architecture as the base object detection model for identifying individual Braille characters within our camera feed. We used the open-source **DotNeuralNet** (by snoop2head) YOLOv8-m weights—which were pretrained on the Angelina Braille dataset—as our foundational model to ensure a generalized baseline.
   - **Customization:** We paired these foundational weights with our proprietary custom Python preprocessing pipeline (CLAHE + Gamma corrections) and a context-aware heuristic autocorrect layer to ensure absolute accuracy on physical braille.

2. **Generative AI Assistants (GitHub Copilot / Google Gemini)**
   - **Purpose:** Used for rapid prototyping, writing boilerplate HTML/CSS for the UI overhaul, and generating regex patterns for our backend fuzzy text matching algorithms. All core logic and architectural integrations were manually designed and verified.

3. **AI Image Generation**
   - **Purpose:** The BrailleVision application logo was generated using AI image generation tools to ensure a high-quality, professional aesthetic for the hackathon presentation.
