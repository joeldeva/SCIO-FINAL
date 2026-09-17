#!/usr/bin/env bash
# =============================================================================
# BrailleVision — Download all external datasets for merge
# Run from the braillevision/ root:  bash download_datasets.sh
#
# Requires: git, python3 with roboflow+pyyaml installed
# Set ROBOFLOW_API_KEY env var before running.
# =============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p datasets

echo "============================================="
echo "  BrailleVision Dataset Downloader"
echo "============================================="
echo ""

# ---- 1. Roboflow datasets (downloaded by merge_datasets.py) ----
echo "[1/3] Roboflow datasets will be downloaded by merge_datasets.py directly."
echo "      Configured sources:"
echo "        - yapayzeka/braille-detection-vxtp1 (~1,324 images)"
echo "        - braille-kp/braille-alphabet-v2 (~313 images)"
echo ""

# ---- 2. Angelina Braille Dataset ----
echo "[2/3] Cloning Angelina Braille Images Dataset..."
if [ -d "datasets/AngelinaDataset" ]; then
    echo "      Already exists, pulling latest..."
    cd datasets/AngelinaDataset && git pull && cd "$SCRIPT_DIR"
else
    git clone --depth 1 https://github.com/IlyaOvodov/AngelinaDataset.git datasets/AngelinaDataset
fi
echo "      Done."
echo ""

# ---- 3. Convert Angelina to YOLO format ----
echo "[3/3] Converting Angelina to YOLO format..."
python3 converters/angelina_to_yolo.py \
    --src datasets/AngelinaDataset \
    --out datasets/angelina_yolo
echo "      Done."
echo ""

echo "============================================="
echo "  All datasets ready!"
echo "  Now run:  python merge_datasets.py"
echo "============================================="
