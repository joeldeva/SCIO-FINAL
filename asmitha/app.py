import os
import threading

import cv2
import numpy as np
import pyttsx3
import streamlit as st
from ultralytics import YOLO


st.set_page_config(
    page_title="BrailleVision",
    page_icon="BV",
    layout="wide",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "runs", "detect", "braille_detector-4", "weights", "best.pt")


@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Model not found: {MODEL_PATH}")
        return None
    return YOLO(MODEL_PATH)


model = load_model()
tts_lock = threading.Lock()


def speak(text: str) -> None:
    def _speak():
        if not tts_lock.acquire(blocking=False):
            return
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        finally:
            tts_lock.release()

    threading.Thread(target=_speak, daemon=True).start()


def get_guidance(frame, detections) -> str:
    brightness = np.mean(frame)
    if brightness < 60:
        return "Too dark. Move to better lighting."
    if brightness > 220:
        return "Too bright. Reduce glare."
    if detections is None or len(detections) == 0:
        return "No Braille detected. Move closer or adjust angle."
    if len(detections) < 3:
        return "Few cells detected. Try moving closer."
    return "Braille detected."


def extract_text_lines(detections, model):
    if detections is None or len(detections) == 0:
        return [], ""

    boxes_data = []
    for box in detections:
        x1 = float(box.xyxy[0][0])
        y1 = float(box.xyxy[0][1])
        cls = int(box.cls[0])
        label = model.names[cls]
        boxes_data.append((y1, x1, label))

    boxes_data.sort(key=lambda item: item[0])

    lines = []
    current_line = [boxes_data[0]]
    for box in boxes_data[1:]:
        if abs(box[0] - current_line[-1][0]) < 30:
            current_line.append(box)
        else:
            lines.append(sorted(current_line, key=lambda item: item[1]))
            current_line = [box]
    lines.append(sorted(current_line, key=lambda item: item[1]))

    letters = [box[2] for line in lines for box in line]
    text_lines = ["".join(box[2] for box in line) for line in lines]
    return letters, "\n".join(text_lines)


def process_image(img, confidence: float, speak_output: bool):
    if model is None:
        return

    results = model(img, conf=confidence, iou=0.3, verbose=False)
    detections = results[0].boxes
    annotated = results[0].plot()
    letters, full_text = extract_text_lines(detections, model)

    st.info(get_guidance(img, detections))
    st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Detection Result", width="stretch")

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Detected Text")
        if full_text:
            st.code(full_text)
        else:
            st.warning("No Braille detected. Try lowering confidence or improving lighting.")
    with right:
        st.subheader("Letters Found")
        st.write(" ".join(letters) if letters else "None")

    if speak_output and full_text:
        speak(full_text)


st.title("BrailleVision - Braille Reader")
st.caption("Laptop webcam mode uses the camera connected to the laptop. Phone mode processes photos from the phone browser.")

st.sidebar.title("Controls")
confidence = st.sidebar.slider("Confidence Threshold", 0.1, 1.0, 0.4)
speak_output = st.sidebar.checkbox("Speak Output on laptop", value=False)
mode = st.sidebar.radio(
    "Input Mode",
    ["Phone snapshot / upload", "Laptop webcam"],
    help="Use phone snapshot/upload when opening this page from your phone.",
)


if mode == "Phone snapshot / upload":
    st.subheader("Phone Snapshot / Upload")
    st.write("Use this mode on your phone. The old live feed used the laptop webcam, not the phone camera.")

    camera_photo = st.camera_input("Take a photo of Braille")
    uploaded = st.file_uploader("Or upload a Braille image", type=["jpg", "jpeg", "png"])

    source = camera_photo or uploaded
    if source is not None:
        file_bytes = np.asarray(bytearray(source.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            st.error("Could not decode image.")
        else:
            process_image(img, confidence, speak_output)
    else:
        st.info("Take a photo or upload an image to run detection.")

else:
    st.subheader("Laptop Webcam")
    st.warning("This mode uses cv2.VideoCapture(0) on the laptop/server, not your phone camera.")
    run_camera = st.checkbox("Start laptop webcam", value=False)
    frame_placeholder = st.empty()
    guidance_placeholder = st.empty()
    text_placeholder = st.empty()

    if run_camera and model is not None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Could not open laptop webcam.")
        else:
            last_spoken = ""
            while run_camera:
                ret, frame = cap.read()
                if not ret:
                    st.error("Camera read failed.")
                    break

                results = model(frame, conf=confidence, iou=0.3, verbose=False)
                detections = results[0].boxes
                guidance_placeholder.info(get_guidance(frame, detections))

                annotated = results[0].plot()
                letters, full_text = extract_text_lines(detections, model)
                text_placeholder.code(full_text if full_text else "Waiting...")

                if speak_output and full_text and full_text != last_spoken:
                    speak(full_text)
                    last_spoken = full_text

                frame_placeholder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB", width="stretch")

            cap.release()
    else:
        frame_placeholder.info("Enable 'Start laptop webcam' to begin.")
