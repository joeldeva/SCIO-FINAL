# Model Class Expansion Plan

The current production model has 26 detector classes, `a` through `z`. The app
and backend now support additional Braille tokens in the decoding layer, but the
model cannot detect them until it is retrained with labeled examples.

## Minimum v2 Class Set

Add these labels to the dataset and train a new YOLO model:

- `number_indicator`
- `capital_indicator`
- `space`
- `period`
- `comma`
- `question`
- `exclamation`
- `colon`
- `semicolon`
- `apostrophe`
- `hyphen`

Useful Grade 2 contractions:

- `the`
- `and`
- `for`
- `of`
- `with`

This moves the detector from 26 classes to at least 37 classes.

## Backend Support Already Added

`backend/scanner_api.py` now handles:

- number mode: `number_indicator` followed by `a-j` becomes `1-0`
- capital mode: `capital_indicator` uppercases the next letter
- punctuation tokens
- common Grade 2 word contractions

## Training Requirement

Every new class needs real labeled boxes from physical Braille images. Synthetic
or clean digital Braille alone will not be enough for reliable camera scanning.

Recommended dataset split:

- normal room lighting
- side lighting
- soft shadows
- close camera distance
- slight tilt
- multiple paper textures
- multiple Braille sizes

Do not replace `backend/model/best.pt` until the new model beats it on the known
test image and several real-book samples.
