import os
import cv2
import sys
sys.path.append('backend')
from inference import run_inference

image_dir = 'dataset/sample_inputs'
print("Evaluating YOLO Model Accuracy:")
print("-" * 50)
correct = 0
total = 0

for file in os.listdir(image_dir):
    if file.endswith('.jpg'):
        expected = file.split('_')[0]
        path = os.path.join(image_dir, file)
        img = cv2.imread(path)
        res = run_inference(img)
        predicted = res['text']
        
        is_correct = expected == predicted
        if is_correct: correct += 1
        total += 1
        
        status = "✅" if is_correct else "❌"
        print(f"{status} {file:25} Expected: {expected:10} Predicted: {predicted}")

print("-" * 50)
print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
