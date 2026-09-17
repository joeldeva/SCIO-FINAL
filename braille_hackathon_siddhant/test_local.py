import cv2
import sys
import os
import glob
from backend.inference import run_inference

def main():
    print("Loading Local Model (Foundation YOLOv8-m) with 4-Stage Pipeline...\n" + "-"*60)
    
    files = [
        "dataset/competitor_pics/judge_test.png",
        "dataset/competitor_pics/braille_book_page.jpg"
    ]
    
    for fp in files:
        if not os.path.exists(fp):
            print(f"File not found: {fp}")
            continue
            
        img = cv2.imread(fp)
        if img is None:
            print(f"Skip (unreadable): {fp}")
            continue
            
        # Run our newly built inference (with difflib, overrides, TTA, Bilateral filter)
        res = run_inference(img)
        text = res.get('text', '')
        
        shown = text.replace("\n", " / ") if text else "(nothing detected)"
        print(f'{os.path.basename(fp):28s} -> "{shown}"')
        
    print("-" * 60 + "\nDone.")

if __name__ == "__main__":
    main()
