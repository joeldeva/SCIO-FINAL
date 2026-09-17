#!/usr/bin/env python3
"""
BrailleVision -- real-time Braille reader (MacBook demo).

Pipeline:  webcam -> (optional CLAHE) -> YOLO cell classifier -> reading-order
decode -> temporal vote -> on-screen text overlay + spoken output.

This targets the CELL-CLASSIFIER model (each detected box's class name is a
letter, e.g. 'a'..'z'). That is your existing prototype and the foolproof
primary path. The dot-detector path needs grid reconstruction (grid.py) and is
a stretch goal only.

Run:
    python app.py --weights model/best.pt
    python app.py --weights model/best.pt --clahe      # if your rig images need contrast

Keys:  q = quit | s = speak current reading | space = pause/resume detection

First run on macOS: grant your terminal/IDE camera permission in
System Settings -> Privacy & Security -> Camera, or you will get black frames.
"""

import argparse
import time
import threading
import queue
import platform
import subprocess
from collections import deque, Counter

import cv2
import numpy as np
from ultralytics import YOLO


# --------------------------------------------------------------------------
# Grade-1 (uncontracted) Braille dot map. Only needed if your model outputs
# dot patterns instead of letters. Kept here so the mapping is documented.
# Cell numbering:   1 4
#                   2 5
#                   3 6
# --------------------------------------------------------------------------
DOTS_TO_CHAR = {
    frozenset({1}): 'a',          frozenset({1, 2}): 'b',        frozenset({1, 4}): 'c',
    frozenset({1, 4, 5}): 'd',    frozenset({1, 5}): 'e',        frozenset({1, 2, 4}): 'f',
    frozenset({1, 2, 4, 5}): 'g', frozenset({1, 2, 5}): 'h',     frozenset({2, 4}): 'i',
    frozenset({2, 4, 5}): 'j',    frozenset({1, 3}): 'k',        frozenset({1, 2, 3}): 'l',
    frozenset({1, 3, 4}): 'm',    frozenset({1, 3, 4, 5}): 'n',  frozenset({1, 3, 5}): 'o',
    frozenset({1, 2, 3, 4}): 'p', frozenset({1, 2, 3, 4, 5}): 'q', frozenset({1, 2, 3, 5}): 'r',
    frozenset({2, 3, 4}): 's',    frozenset({2, 3, 4, 5}): 't',  frozenset({1, 3, 6}): 'u',
    frozenset({1, 2, 3, 6}): 'v', frozenset({2, 4, 5, 6}): 'w',  frozenset({1, 3, 4, 6}): 'x',
    frozenset({1, 3, 4, 5, 6}): 'y', frozenset({1, 3, 5, 6}): 'z',
}


# --------------------------------------------------------------------------
# Non-blocking speaker. Uses macOS `say` (rock-solid, zero install on the M2);
# falls back to pyttsx3 on other OSes. TTS runs in its own thread so it never
# freezes the video loop.
# --------------------------------------------------------------------------
class Speaker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.q = queue.Queue()
        self.is_mac = platform.system() == "Darwin"
        self.start()

    def run(self):
        engine = None
        if not self.is_mac:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
        while True:
            text = self.q.get()
            if text is None:
                break
            try:
                if self.is_mac:
                    subprocess.run(["say", text])
                else:
                    engine.say(text)
                    engine.runAndWait()
            except Exception as e:
                print("TTS error:", e)

    def say(self, text):
        # drop anything queued so we always speak the most recent reading
        with self.q.mutex:
            self.q.queue.clear()
        self.q.put(text)

    def stop(self):
        self.q.put(None)


# --------------------------------------------------------------------------
# Turn a set of detections into text in correct reading order.
# dets: list of (cx, cy, label, box_height)
# --------------------------------------------------------------------------
def reading_order(dets, line_tol_frac=0.6, space_mult=1.7):
    if not dets:
        return ""
    med_h = float(np.median([d[3] for d in dets]))
    line_tol = med_h * line_tol_frac

    # group into text-lines by y
    dets = sorted(dets, key=lambda d: d[1])
    lines, cur = [], [dets[0]]
    for d in dets[1:]:
        if abs(d[1] - cur[-1][1]) <= line_tol:
            cur.append(d)
        else:
            lines.append(cur)
            cur = [d]
    lines.append(cur)

    out = []
    for ln in lines:
        ln = sorted(ln, key=lambda d: d[0])  # left to right
        text = ln[0][2]
        for prev, d in zip(ln, ln[1:]):
            if (d[0] - prev[0]) > med_h * space_mult:   # wide gap => space
                text += " "
            text += d[2]
        out.append(text)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="model/best.pt")
    ap.add_argument("--cam", type=int, default=0, help="camera index (try 1 if 0 is wrong)")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--vote", type=int, default=5, help="frames of temporal voting")
    ap.add_argument("--space_mult", type=float, default=1.7)
    ap.add_argument("--every", type=int, default=1, help="run detection every Nth frame")
    ap.add_argument("--clahe", action="store_true", help="apply CLAHE contrast before detection")
    args = ap.parse_args()

    print("Loading model:", args.weights)
    model = YOLO(args.weights)
    names = model.names
    speaker = Speaker()
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("ERROR: could not open camera. Try --cam 1, and check camera permission.")
        return

    history = deque(maxlen=args.vote)
    stable = ""
    last_spoken = ""
    last_emit = 0.0
    paused = False
    fcount = 0
    fps_t, fps = time.time(), 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        fcount += 1

        proc = frame
        if args.clahe:
            g = clahe.apply(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            proc = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)

        if not paused and fcount % args.every == 0:
            res = model.predict(proc, conf=args.conf, verbose=False)[0]
            dets = []
            for b in res.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                label = names[int(b.cls[0])]
                dets.append(((x1 + x2) / 2, (y1 + y2) / 2, label, y2 - y1))
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 230, 0), 2)
                cv2.putText(frame, label, (int(x1), int(y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)
            history.append(reading_order(dets, space_mult=args.space_mult))
            if history:
                stable = Counter(history).most_common(1)[0][0]

        # FPS
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-6, now - fps_t))
        fps_t = now

        # text panel
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 44), (0, 0, 0), -1)
        cv2.putText(frame, "READ: " + stable.replace("\n", " / "), (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, f"{fps:4.1f} fps  {'PAUSED' if paused else ''}",
                    (frame.shape[1] - 230, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

        cv2.imshow("BrailleVision", frame)

        # speak when the reading settles into something new
        if stable and stable != last_spoken and (now - last_emit) > 1.2:
            speaker.say(stable.replace("\n", ". "))
            last_spoken, last_emit = stable, now

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        elif k == ord("s") and stable:
            speaker.say(stable.replace("\n", ". "))
        elif k == ord(" "):
            paused = not paused

    cap.release()
    cv2.destroyAllWindows()
    speaker.stop()


if __name__ == "__main__":
    main()
