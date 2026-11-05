"""Raw recognition regression on repository photographs, never a production accuracy claim."""
import argparse,csv,hashlib,json,platform,statistics,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
ROOT=BACKEND.parents[1]
sys.path.insert(0,str(BACKEND))
import cv2
import numpy as np
import torch
torch.set_num_threads(2)
import scanner_api

def distance(a,b):
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        row=[i]
        for j,right in enumerate(b,1): row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=row
    return previous[-1]

def variants(image):
    h,w=image.shape[:2]
    yield 'original',image
    yield 'dim_50_percent',(image.astype(np.float32)*.5).astype(np.uint8)
    yield 'gaussian_blur_7px',cv2.GaussianBlur(image,(7,7),2)
    yield 'rotation_8_degrees',cv2.warpAffine(image,cv2.getRotationMatrix2D((w/2,h/2),8,.9),(w,h),borderValue=(255,255,255))
    matrix=cv2.getPerspectiveTransform(np.float32([[0,0],[w,0],[w,h],[0,h]]),np.float32([[w*.08,h*.03],[w*.94,0],[w,h*.96],[0,h]]))
    yield 'synthetic_perspective',cv2.warpPerspective(image,matrix,(w,h),borderValue=(255,255,255))

def evaluate(predict):
    cases=[]
    with (ROOT/'sciobraille-model-lab/benchmark/ground_truth.csv').open(newline='') as file:
        for row in csv.DictReader(file):
            path=ROOT/row['image_path'];image=cv2.imread(str(path))
            if image is None: raise RuntimeError(f'Missing image {path}; fetch Git LFS assets')
            expected=row['ground_truth'].strip();flip={'true':True,'false':False}.get(row['flip_horizontal'].lower())
            for variant,frame in variants(image):
                durations=[]
                for _ in range(3):
                    start=time.perf_counter();payload=predict(frame,flip_horizontal=flip);durations.append((time.perf_counter()-start)*1000)
                raw=payload['raw_text'].strip()
                cases.append(dict(id=row['id'],variant=variant,image=row['image_path'],image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),expected=expected,raw_text=raw,cer=distance(expected,raw)/max(1,len(expected)),wer=distance(expected.split(),raw.split())/max(1,len(expected.split())),median_predict_ms=statistics.median(durations),detections=payload['detections'],confidence=payload['confidence'],mirrored=payload['input_flipped_horizontal']))
    return cases

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--baseline');args=parser.parse_args()
    scanner_api._predict(np.full((640,640,3),127,np.uint8),flip_horizontal=False)
    result=dict(model_sha256=hashlib.sha256(scanner_api.MODEL_PATH.read_bytes()).hexdigest(),runtime=dict(python=platform.python_version(),platform=platform.platform(),torch=torch.__version__,threads=2),scope='3 repository photographs plus 12 synthetic variants; not independent or representative. Predictions only, excluding camera/network.',current=evaluate(scanner_api._predict))
    if args.baseline:
        import importlib.util,os
        os.environ['MODEL_PATH']=str(scanner_api.MODEL_PATH)
        spec=importlib.util.spec_from_file_location('baseline_scanner',args.baseline);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module._predict(np.full((640,640,3),127,np.uint8),flip_horizontal=False)
        result['baseline']=evaluate(module._predict)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for key in ['current','baseline']:
        if key not in result: continue
        rows=[x for x in result[key] if x['variant']=='original']
        print(key,'macro CER',statistics.mean(x['cer'] for x in rows),'macro WER',statistics.mean(x['wer'] for x in rows),'median prediction ms',statistics.median(x['median_predict_ms'] for x in rows))
