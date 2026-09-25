# Sciobraille V2 Master Model

## Selected Model Details
- **Architecture:** YOLOv8s
- **Candidate Name:** `yolov8s_master_v2`
- **Checkpoint SHA-256:** `8e32d074e0edb12cf6667310dd45b5cb5b4b837979c80289b15028918e831e62`
- **Classes:** 26 canonical classes (`0=a` through `25=z`)
- **Input Resolution:** 640 x 640
- **Model File:** `best.pt`

## Dataset Lineage
- **Dataset:** Master V2 (deduplicated across Prabh merged, Sangam, and Asmitha)
- **Train Images:** 1,440
- **Validation Images:** 165
- **Internal Test Images:** 179
- **Total Retained Images:** 1784
- **Total Bounding Boxes:** 1784

## Performance Metrics
- **Validation mAP50-95:** 0.8050
- **Validation mAP50:** 0.9629
- **Validation Recall:** 0.9326
- **Validation Precision:** 0.9650
- **Internal Test mAP50-95:** 0.7924
- **Internal Test mAP50:** 0.9535
- **Inference Latency:** 15.65 ms (desktop GPU)
- **Physical Benchmark CER:** 0.3963 (regression check only)

## Verification
- Loaded and verified via Ultralytics YOLO.
- Production model `sciobraille-scanner/backend/model/best.pt` preserved with SHA-256 `b9269091c92be04c461596d8c2254e593864c7bce02c1b2a439837a7cc99f974`.
