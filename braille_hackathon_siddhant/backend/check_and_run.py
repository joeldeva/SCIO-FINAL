"""
BrailleVision - Quick Setup Checker
Run this to verify all dependencies are installed and everything is ready.
"""

import sys
import subprocess

REQUIRED = {
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'cv2': 'opencv-python',
    'numpy': 'numpy',
    'PIL': 'pillow',
    'gtts': 'gtts',
    'aiofiles': 'aiofiles',
}

OPTIONAL = {
    'ultralytics': 'ultralytics (YOLOv8)',
}

print("\n" + "="*55)
print("  BrailleVision - Dependency Check")
print("="*55)

all_ok = True
for module, pkg in REQUIRED.items():
    try:
        __import__(module)
        print(f"  ✅  {pkg:<30} installed")
    except ImportError:
        print(f"  ❌  {pkg:<30} MISSING")
        all_ok = False

print()
for module, pkg in OPTIONAL.items():
    try:
        __import__(module)
        print(f"  ✅  {pkg:<30} installed (YOLO enabled!)")
    except ImportError:
        print(f"  ⚠️   {pkg:<30} not installed (using classical CV)")

print("="*55)
if all_ok:
    print("  🚀 All dependencies OK! Starting server...\n")
    import subprocess
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                   cwd=str(__import__('pathlib').Path(__file__).parent))
else:
    print("  ⚠️  Some dependencies missing.")
    print("  Run: install_remaining.bat or install manually.")
    print("="*55 + "\n")
    sys.exit(1)
