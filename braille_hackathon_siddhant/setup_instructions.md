# Setup Instructions

Follow these instructions to run the BrailleVision project locally. The project requires Python 3.10+ and Node.js (for serving the frontend, or you can just open the HTML file directly).

### 1. Clone the Repository
```bash
git clone https://github.com/SiddGud/braille_hackathon_siddhant.git
cd braille_hackathon_siddhant
```

### 2. Backend Setup
The backend runs on Python via FastAPI and Ultralytics YOLOv8.

```bash
# Optional: Create a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Start the Backend Server (Runs on port 8000)
python backend/app.py
```
*Note: The backend will automatically load the YOLO weights from `model/best.pt`.*

### 3. Frontend Setup
The frontend consists of vanilla HTML, CSS, and JS. It requires no complex build tools.

**Option A (Recommended):**
Simply double-click `frontend/index.html` to open it in your browser.

**Option B (Local Web Server):**
If you prefer to run it via a local server to avoid CORS issues:
```bash
# Using Python
cd frontend
python -m http.server 3000
# Then open http://localhost:3000 in your browser
```

### 4. How to Test Inference
1. Make sure the backend server is running (`python backend/app.py`).
2. Open `frontend/index.html` in your browser.
3. Click **Live Stream** to use your webcam, or **Upload Image** to test a pre-captured photo.
4. If testing via upload, you can use the sample images located in the `sample_inputs/` folder.

**Mandatory Lighting Note:** When testing physical Braille, please ensure the paper is laid flat, face down (so dots are indented), and a flashlight is pointed from the bottom-left corner across the page. This accurately recreates the shadow conditions the model was trained on.
