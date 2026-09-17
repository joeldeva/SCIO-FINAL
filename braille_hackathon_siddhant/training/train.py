from ultralytics import YOLO
import os
import shutil
from pathlib import Path

def main():
    print("=" * 70)
    print("  BrailleVision - YOLOv8n Fine-Tuning Pipeline")
    print("=" * 70)

    dataset_yaml = os.path.abspath("dataset/data.yaml")
    
    if not os.path.exists(dataset_yaml):
        print("\n[!] Dataset not found locally. To download from Roboflow:")
        print("  1. Go to https://universe.roboflow.com/search?q=braille")
        print("  2. Click any good dataset, select 'YOLOv8' format, and click 'Show Download Code'")
        return

    # Load YOLOv8 nano
    print("[*] Loading yolov8n.pt...")
    model = YOLO("yolov8n.pt")

    print("[*] Starting training loop...")
    
    results = model.train(
        data=dataset_yaml,
        epochs=50,              # Fine-tuned for 50 epochs
        imgsz=640,              # Standard YOLOv8 size
        batch=8,                # Optimized for lower-tier hardware constraints (T4 GPU)
        cache=False,            # Disabled dataset caching to prevent RAM exhaustion
        name="braille_yolov8n",
        
        # --- CRITICAL AUGMENTATION CHOICES ---
        
        # Braille is chiral (direction-sensitive)
        fliplr=0.0,             # Prevents w -> r hallucination
        flipud=0.0,             # Prevents a -> e hallucination
        
        # Other standard augmentations
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        mosaic=1.0,
        
        plots=True,
        verbose=True,
        optimizer='AdamW'
    )
    
    best_pt_src = Path("runs/detect/braille_yolov8n/weights/best.pt")
    best_pt_dst = Path("model/best.pt")
    
    if best_pt_src.exists():
        best_pt_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_pt_src, best_pt_dst)
        print(f"\n[SUCCESS] Fine-tuned model saved to {best_pt_dst}")
    else:
        print(f"\n[ERROR] Training finished but {best_pt_src} was not found.")

if __name__ == "__main__":
    main()
