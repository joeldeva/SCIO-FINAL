@echo off
set BRAILLE_HOST=0.0.0.0
set BRAILLE_PORT=8089
set MODEL_PATH=../../sciobraille-model-lab/models/v2_master/best.pt
echo Starting Sciobraille V2 Test Backend on port 8089...
python scanner_api.py
