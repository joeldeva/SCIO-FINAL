# AI Tools Disclosure

## Team: The Decoders

### AI Tools Used

| Tool | Purpose | What we used it for |
|------|---------|-------------------|
| **Claude Opus 4** | Code generation & planning | Initial project skeleton, architecture planning, code review |
| **Chatgpt (Codex)** | Dataset engineering & automation | Dataset merging pipeline, Angelina bitmask converter, training scripts, documentation |
| **Roboflow** | Dataset management | Hosting and downloading labeled Braille detection images via API |
| **Kaggle GPU** | Model training | Training 3 YOLO variants on T4 GPUs across 2 accounts |

### What was NOT AI-generated

- Dataset curation decisions (which datasets to use, which to reject)
- Model architecture strategy (3-variant comparison approach)
- Transfer learning decision (using DotNeuralNet braille backbone)
- All training hyperparameter tuning
- Real-world testing and validation
- Final model selection based on metrics comparison

### Human Contributions

- **Prabhpreet Singh**: Project ideation, dataset selection, Kaggle training execution, model evaluation, demo testing, final submission
- **AI Assistants**: Code scaffolding, documentation, dataset format conversion automation

### Proper Attribution

All external datasets and pretrained models are credited in README.md and docs/model_journey.md:
- Angelina Braille Dataset (Ilya Ovodov, GitHub)
- DotNeuralNet pretrained weights (snoop2head, GitHub)
- yapayzeka/braille-detection-vxtp1 (Roboflow Universe)
- Ultralytics YOLOv8/v11 framework
