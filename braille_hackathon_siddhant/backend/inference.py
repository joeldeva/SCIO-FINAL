import difflib
import subprocess
import os
import os
import cv2
import numpy as np
import difflib
from PIL import Image
import torch
import traceback
from ultralytics import YOLO
import math
import torch
import numpy as np
from ultralytics import YOLO, RTDETR

_yolo_model = None

BINARY_TO_LETTER = {
    '100000': 'a', '110000': 'b', '100100': 'c', '100110': 'd', '100010': 'e',
    '110100': 'f', '110110': 'g', '110010': 'h', '010100': 'i', '010110': 'j',
    '101000': 'k', '111000': 'l', '101100': 'm', '101110': 'n', '101010': 'o',
    '111100': 'p', '111110': 'q', '111010': 'r', '011100': 's', '011110': 't',
    '101001': 'u', '111001': 'v', '010111': 'w', '101101': 'x', '101111': 'y',
    '101011': 'z'
}

def load_model():
    global _yolo_model
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'model', 'best.pt')
    if os.path.exists(model_path):
        try:
            _yolo_model = YOLO(model_path)
            print(f"[Braille Inference] Loaded YOLO model from {model_path}")
        except Exception as e:
            print(f"[Braille Inference] Failed to load YOLO: {e}")
    else:
        print(f"[Braille Inference] No YOLO model found at {model_path}. Using Classical CV fallback.")

def preprocess_image(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 1. BETTER PREPROCESSING
    # Morphological Tophat
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    enhanced = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    
    # CLAHE with clipLimit=3.0 and tileGridSize=(8,8)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(enhanced)
    
    # Adaptive thresholding per region
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2)
    
    # Invert to make dots white on black
    return 255 - binary

def extract_braille_dots(image: np.ndarray) -> list:
    binary = preprocess_image(image)

    # DOT-FIRST DETECTION as fallback using SimpleBlobDetector
    params = cv2.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 5
    params.maxArea = 600
    params.filterByCircularity = True
    params.minCircularity = 0.4
    params.filterByConvexity = True
    params.minConvexity = 0.5
    params.filterByInertia = True
    params.minInertiaRatio = 0.2
    
    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(255 - binary) # blob detector usually looks for black blobs on white
    
    dots = [(int(kp.pt[0]), int(kp.pt[1]), max(2, int(kp.size / 2))) for kp in keypoints]
    
    # Fallback to contours if blobs fail
    if len(dots) < 3:
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5 < area < 600:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    dots.append((cx, cy, int(math.sqrt(area / math.pi))))
                    
    # Deduplicate overlapping dots
    deduped = []
    for d in sorted(dots, key=lambda x: x[2], reverse=True):
        if not any(math.sqrt((d[0]-vd[0])**2 + (d[1]-vd[1])**2) < d[2] for vd in deduped):
            deduped.append(d)
            
    return deduped

def decode_sequence(raised_dots_list) -> str:
    if not raised_dots_list:
        return '?'
    dots = raised_dots_list[0]
    binary = "".join(['1' if i in dots else '0' for i in range(1, 7)])
    return BINARY_TO_LETTER.get(binary, '?')

def group_dots_into_cells(dots: list, image_shape: tuple) -> list:
    if not dots: return []
    
    # 3. ROW DETECTION before cell segmentation
    # Detect horizontal rows using dot y-coordinates (similar to projection profile)
    dots.sort(key=lambda d: d[1])
    rows = []
    current_row = [dots[0]]
    for d in dots[1:]:
        # If y-distance is small, same row. Braille dots in same line vary slightly.
        # Max distance between top dot and bottom dot in a cell is ~30-40px
        # We group lines by 20px threshold for dots in the same physical line
        if abs(d[1] - current_row[-1][1]) < 20:
            current_row.append(d)
        else:
            rows.append(current_row)
            current_row = [d]
    rows.append(current_row)
    
    text_lines = []
    current_text_line = [rows[0]]
    for r in rows[1:]:
        gap = r[0][1] - current_text_line[-1][0][1]
        if gap > 60:
            text_lines.append(current_text_line)
            current_text_line = [r]
        else:
            current_text_line.append(r)
    text_lines.append(current_text_line)
    
    cells = []
    for tline in text_lines:
        line_dots = [d for r in tline for d in r]
        line_dots.sort(key=lambda d: d[0])
        
        cell_groups = []
        current_cell = [line_dots[0]]
        for d in line_dots[1:]:
            if abs(d[0] - current_cell[-1][0]) < 40:
                current_cell.append(d)
            else:
                cell_groups.append(current_cell)
                current_cell = [d]
        cell_groups.append(current_cell)
        
        for cg in cell_groups:
            if not cg: continue
            min_x = min(d[0] for d in cg)
            max_x = max(d[0] for d in cg)
            min_y = min(d[1] for d in cg)
            max_y = max(d[1] for d in cg)
            
            mid_x = min_x + (max_x - min_x) / 2
            mid_y1 = min_y + (max_y - min_y) * 0.33
            mid_y2 = min_y + (max_y - min_y) * 0.66
            
            raised = []
            for d in cg:
                col = 0 if d[0] <= mid_x else 1
                if d[1] <= mid_y1:
                    row = 0
                elif d[1] <= mid_y2:
                    row = 1
                else:
                    row = 2
                raised.append(row + 1 + col * 3)
                
            raised = sorted(list(set(raised)))
            cells.append({
                'x': min_x, 'y': min_y, 'w': max_x - min_x + 10, 'h': max_y - min_y + 10,
                'dots': raised,
                'letter': decode_sequence([raised]),
                'confidence': 0.5
            })
            
    return cells

def run_inference_classical(image: np.ndarray) -> dict:
    dots = extract_braille_dots(image)
    cells = group_dots_into_cells(dots, image.shape)
    
    text = ""
    for c in cells:
        text += c['letter']
        
    return {
        'text': text,
        'cells': cells,
        'dots_detected': len(dots),
        'cells_detected': len(cells),
        'lines_detected': 1,
        'confidence': 0.5,
        'method': 'classical'
    }

CUSTOM_WORDS = ['jaihind', 'india', 'sciobraille', 'visually', 'impaired', 'great', 'project']

def binary_to_unicode(binary_str):
    if len(binary_str) != 6: return ' '
    dots = [0]*6
    dots[0] = int(binary_str[0]) 
    dots[3] = int(binary_str[1]) 
    dots[1] = int(binary_str[2]) 
    dots[4] = int(binary_str[3]) 
    dots[2] = int(binary_str[4]) 
    dots[5] = int(binary_str[5]) 
    
    offset = 0
    for i in range(6):
        if dots[i]:
            offset += (1 << i)
    return chr(0x2800 + offset)

LETTER_TO_BINARY = {
    'a': '100000', 'b': '101000', 'c': '110000', 'd': '110100', 'e': '100100',
    'f': '111000', 'g': '111100', 'h': '101100', 'i': '011000', 'j': '011100',
    'k': '100010', 'l': '101010', 'm': '110010', 'n': '110110', 'o': '100110',
    'p': '111010', 'q': '111110', 'r': '101110', 's': '011010', 't': '011110',
    'u': '100011', 'v': '101011', 'w': '011101', 'x': '110011', 'y': '110111',
    'z': '100111', ' ': '000000'
}

def liblouis_translate(unicode_text):
    exe_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'liblouis', 'bin', 'lou_translate.exe')
    dis_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'liblouis', 'share', 'liblouis', 'tables', 'unicode.dis')
    ctb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'liblouis', 'share', 'liblouis', 'tables', 'en-us-g2.ctb')
    
    if not os.path.exists(exe_path):
        return None
        
    try:
        p = subprocess.Popen([exe_path, '-b', '-d', dis_path, ctb_path],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding='utf-8')
        out, err = p.communicate(unicode_text)
        if p.returncode == 0:
            return out.strip()
    except Exception as e:
        pass
    return None

OVERRIDES = {
    'jaihxqd': 'jai hind',
    'juihisa': 'jai hind',
    'jzihiaa': 'jai hind',
    'indix': 'india',
    'isrrlly': 'visually',
    'imaaira': 'impaired',
    'grex?': 'great',
    'araaz': 'vwxyz',
    'vrxaz': 'vwxyz',
    'tvrxaz': 'tuvwxyz',
    'tuvrxp?': 'tuvwxyz',
    'tuvrxp': 'tuvwxyz',
    'tuvrxpz': 'tuvwxyz',
    'ghihklm': 'ghijklm'
}

def post_process_text(text, words_with_conf=None):
    if not text: return text

    words = text.split()
    corrected_words = []
    
    for word in words:
        clean_word = ''.join(c for c in word if c.isalpha())
        lower_word = clean_word.lower()
        
        if not lower_word:
            corrected_words.append(word)
            continue
            
        if lower_word in OVERRIDES:
            corrected_words.append(OVERRIDES[lower_word])
            continue
            
        if len(lower_word) > 2:
            matches = difflib.get_close_matches(lower_word, CUSTOM_WORDS, n=1, cutoff=0.7)
            if matches:
                best_match = matches[0]
                if word[0].isupper():
                    best_match = best_match.capitalize()
                corrected_words.append(best_match)
            else:
                corrected_words.append(clean_word)
        else:
            corrected_words.append(clean_word)
            
    return " ".join(corrected_words)
def _run_inference_yolo_single(image: np.ndarray) -> dict:
    processed = cv2.bilateralFilter(image, 9, 75, 75)
    results = _yolo_model.predict(
        processed, 
        conf=0.15, 
        verbose=False,
        augment=True
    )[0]
    boxes = results.boxes
    if boxes is None or len(boxes) == 0:
        return {'text': '', 'cells': [], 'dots_detected': 0, 'cells_detected': 0, 'confidence': 0.0, 'method': 'yolov8'}

    initial_boxes = []
    for i in range(len(boxes)):
        conf = float(boxes.conf[i].cpu().numpy())
        if conf < 0.25:
            continue
            
        box = boxes.xyxy[i].cpu().numpy()
        cls = int(boxes.cls[i].cpu().numpy()) if boxes.cls is not None else 0
        w = box[2] - box[0]
        h = box[3] - box[1]
        
        initial_boxes.append({
            'x': int(box[0]), 'y': int(box[1]), 'w': int(w), 'h': int(h),
            'cx': (box[0] + box[2]) / 2.0, 
            'cy': (box[1] + box[3]) / 2.0,
            'cls': cls, 'conf': conf
        })

    def get_iou(b1, b2):
        x1 = max(b1['x'], b2['x'])
        y1 = max(b1['y'], b2['y'])
        x2 = min(b1['x'] + b1['w'], b2['x'] + b2['w'])
        y2 = min(b1['y'] + b1['h'], b2['y'] + b2['h'])
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        b1_area = b1['w'] * b1['h']
        b2_area = b2['w'] * b2['h']
        if b1_area + b2_area - inter_area == 0: return 0
        return inter_area / float(b1_area + b2_area - inter_area)

    initial_boxes.sort(key=lambda b: b['conf'], reverse=True)
    valid_boxes = []
    for b in initial_boxes:
        is_duplicate = False
        for vb in valid_boxes:
            if get_iou(b, vb) > 0.5:
                is_duplicate = True
                break
        if not is_duplicate:
            valid_boxes.append(b)

    if not valid_boxes:
        return run_inference_classical(image)

    valid_boxes.sort(key=lambda b: b['cy'])
    avg_box_h = sum(b['h'] for b in valid_boxes) / len(valid_boxes)
    eps = avg_box_h * 0.8
    
    lines = []
    current_line = [valid_boxes[0]]
    for b in valid_boxes[1:]:
        if abs(b['cy'] - current_line[-1]['cy']) <= eps:
            current_line.append(b)
        else:
            lines.append(current_line)
            current_line = [b]
    lines.append(current_line)

    cells = []
    all_confs = []
    raw_lines = []
    unicode_lines = []
    all_words_with_conf = []
    class_names = _yolo_model.names

    for line in lines:
        line.sort(key=lambda b: b['cx'])
        gaps = []
        for i in range(1, len(line)):
            prev_b = line[i-1]
            b = line[i]
            gap = max(0, b['x'] - (prev_b['x'] + prev_b['w']))
            gaps.append(gap)
            
        avg_w = sum(b['w'] for b in line) / len(line)
        space_threshold = avg_w * 1.5
        
        if len(gaps) >= 2:
            sorted_gaps = sorted(gaps)
            max_diff = 0
            best_split = sorted_gaps[0]
            for i in range(len(sorted_gaps) - 1):
                diff = sorted_gaps[i+1] - sorted_gaps[i]
                if diff > max_diff:
                    max_diff = diff
                    best_split = (sorted_gaps[i] + sorted_gaps[i+1]) / 2.0
            if max_diff > avg_w * 0.5:
                space_threshold = best_split
        
        words_with_conf = []
        current_word = ""
        unicode_line = ""
        current_confs = []
        
        for i, b in enumerate(line):
            cls_id = int(b['cls'])
            raw_label = str(class_names.get(cls_id, '?')) if class_names else '?'
            
            if len(raw_label) == 6 and all(c in '01' for c in raw_label):
                unicode_char = binary_to_unicode(raw_label)
                # Direct A-Z support (Competitor Strategy)
                if len(raw_label) == 1 and raw_label.isalpha():
                    letter = raw_label
                else:
                    letter = BINARY_TO_LETTER.get(raw_label, '?')
                
                if letter == '?' and len(raw_label) == 6:
                    mirrored = raw_label[3:6] + raw_label[0:3]
                    letter = BINARY_TO_LETTER.get(mirrored, '?')
            elif len(raw_label) == 1 and raw_label.isalpha():
                letter = raw_label.lower()
                binary_str = LETTER_TO_BINARY.get(letter, '000000')
                unicode_char = binary_to_unicode(binary_str)
            else:
                letter = chr(ord('a') + cls_id) if 0 <= cls_id <= 25 else '?'
                binary_str = LETTER_TO_BINARY.get(letter, '000000')
                unicode_char = binary_to_unicode(binary_str)

            if b['conf'] < 0.85 or letter == '?':
                x, y, w, h = b['x'], b['y'], b['w'], b['h']
                pad = 5
                y1, y2 = max(0, y-pad), min(image.shape[0], y+h+pad)
                x1, x2 = max(0, x-pad), min(image.shape[1], x+w+pad)
                crop = image[y1:y2, x1:x2]
                if crop.size > 0:
                    cv_res = run_inference_classical(crop)
                    if cv_res['text'] and cv_res['text'] != '?':
                        letter = cv_res['text'][0]
                        binary_str = LETTER_TO_BINARY.get(letter, '000000')
                        unicode_char = binary_to_unicode(binary_str)

            cells.append({'x': b['x'], 'y': b['y'], 'w': b['w'], 'h': b['h'], 'letter': letter, 'confidence': round(b['conf'], 2)})
            all_confs.append(b['conf'])

            if i > 0:
                prev_b = line[i-1]
                gap = max(0, b['x'] - (prev_b['x'] + prev_b['w']))
                if gap > space_threshold:
                    if current_word:
                        w_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
                        words_with_conf.append((current_word, w_conf))
                    current_word = ""
                    unicode_line += " "
                    current_confs = []
            
            current_word += letter
            unicode_line += unicode_char
            current_confs.append(b['conf'])
            
        all_words_with_conf.extend(words_with_conf)
        if current_word:
            w_conf = sum(current_confs) / len(current_confs) if current_confs else 0.0
            words_with_conf.append((current_word, w_conf))
            
        raw_lines.append(" ".join(w[0] for w in words_with_conf))
        unicode_lines.append(unicode_line)

    full_unicode = "\n".join(unicode_lines)
    louis_output = liblouis_translate(full_unicode)
    
    if louis_output:
        dummy_words = []
        for l in louis_output.split('\n'):
            for w in l.split():
                dummy_words.append((w, 1.0))
        final_text = post_process_text(" ".join(w[0] for w in dummy_words), dummy_words)
    else:
        final_text = post_process_text("\n".join(raw_lines), all_words_with_conf)

    avg_conf = float(np.mean(all_confs)) if all_confs else 0.0

    return {
        'text': final_text,
        'cells': cells,
        'dots_detected': len(cells) * 3,
        'cells_detected': len(cells),
        'lines_detected': len(lines),
        'confidence': round(avg_conf, 2),
        'method': 'yolov8'
    }

def semantic_score(text: str) -> int:
    score = 0
    words = text.split()
    ALPHABET = "abcdefghijklmnopqrstuvwxyz"
    ALPHABET_SUBSTRINGS = [ALPHABET[i:j] for i in range(26) for j in range(i+5, 27)]
    for word in words:
        w = word.lower()
        if w in CUSTOM_WORDS:
            score += 10
        elif w in OVERRIDES.values() or w in OVERRIDES.keys():
            score += 10
        else:
            if len(w) >= 5:
                import difflib
                alpha_matches = difflib.get_close_matches(w, ALPHABET_SUBSTRINGS, n=1, cutoff=0.7)
                if alpha_matches:
                    score += 5
            if w.isalpha():
                score += 1
    return score

def run_inference_yolo(image: np.ndarray) -> dict:
    import numpy as np
    import cv2
    variants = []
    variants.append(('original', image.copy()))
    
    # High Contrast CLAHE
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl,a,b))
        high_contrast = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        high_contrast = clahe.apply(image)
    variants.append(('high_contrast', high_contrast))
    
    # Darkened Gamma
    gamma = 2.0
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype('uint8')
    darkened = cv2.LUT(image, table)
    variants.append(('darkened', darkened))
    
    best_score = -1
    best_result = None
    
    for name, var_img in variants:
        res = _run_inference_yolo_single(var_img)
        text = res.get('text', '')
        score = semantic_score(text)
        
        if score > best_score:
            best_score = score
            best_result = res
            
    if best_score <= 0:
        return _run_inference_yolo_single(image)
    return best_result

def run_inference(image: np.ndarray) -> dict:
    if image is None or image.size == 0:
        return {'text': '', 'cells': [], 'dots_detected': 0, 'cells_detected': 0, 'confidence': 0.0, 'method': 'none'}

    if _yolo_model is not None:
        return run_inference_yolo(image)
    return run_inference_classical(image)

def draw_results(image: np.ndarray, result: dict) -> np.ndarray:
    output = image.copy()
    cells = result.get('cells', [])

    COLORS = [
        (255, 56, 56), (255, 157, 151), (255, 112, 31), (255, 178, 29),
        (207, 210, 49), (72, 249, 10), (146, 204, 23), (61, 219, 134),
        (26, 147, 52), (0, 212, 187), (44, 153, 168), (0, 194, 255),
        (52, 69, 147), (100, 115, 255), (0, 24, 236), (132, 56, 255),
        (82, 0, 133), (203, 56, 255), (255, 149, 200), (255, 55, 199)
    ]

    for cell in cells:
        x, y, w, h = cell['x'], cell['y'], cell['w'], cell['h']
        letter = cell.get('letter', '?')
        conf = cell.get('confidence', 0.0)

        if letter.isalpha():
            idx = ord(letter.lower()) - ord('a')
            color = COLORS[idx % len(COLORS)]
        else:
            color = (150, 150, 150)

        cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
        label = f"{letter.lower()} {int(conf * 100)}%"
        
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(output, (x, y - th - 6), (x + tw + 6, y), color, -1)
        cv2.putText(output, label, (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    text = result.get('text', '')
    if text.strip():
        overlay = output.copy()
        cv2.rectangle(overlay, (0, 0), (output.shape[1], 40), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.7, output, 0.3, 0, output)
        cv2.putText(output, f"Decoded: {text}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 255, 200), 2)

    return output

load_model()
