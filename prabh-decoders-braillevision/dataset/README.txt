Add to this folder:
  data.yaml            <- class names (a-z) + train/val paths
  sample_images/       <- a few representative training images
  sample_annotations/  <- matching YOLO .txt labels for those images
The FULL dataset stays on Roboflow/Drive (link it in dataset_info.md).
Regenerate the merged training set any time with:  python ../merge_datasets.py
