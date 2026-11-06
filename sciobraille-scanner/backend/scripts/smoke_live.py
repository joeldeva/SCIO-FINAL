"""Explicit network smoke test; --community sends only fixed public sample text.
No human translation-quality verdict is inferred from a successful response.
"""
import argparse,asyncio,json,sys,time
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1];ROOT=BACKEND.parents[1];sys.path.insert(0,str(BACKEND))
import torch
torch.set_num_threads(2)
from fastapi.testclient import TestClient
import scanner_api
from translation_service import TranslationService

async def translations():
    service=TranslationService('community');results=[]
    for lang in ['ta','hi','te','ml','kn','bn','ar','zh-CN','zh-TW','ja','fr','sa','or','as']:
        start=time.perf_counter()
        try:
            value=await service.translate('Welcome. Learning Braille connects us.','en',lang)
            results.append(dict(target=lang,status='response_received',translated=value.text,milliseconds=round((time.perf_counter()-start)*1000)))
        except Exception as error: results.append(dict(target=lang,status='failed',error=str(error)))
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--community',action='store_true');args=parser.parse_args()
    image=(ROOT/'sciobraille-model-lab/benchmark/images/test_sciobraille.jpeg').read_bytes()
    with TestClient(scanner_api.app) as client:
        response=client.post('/api/scan-frame?flip_horizontal=false',files={'frame':('physical.jpg',image,'image/jpeg')})
        assert response.status_code==200 and response.json()['detections']>0
        with client.websocket_connect('/ws/scan?flip_horizontal=false') as ws:
            ws.send_bytes(image);first=ws.receive_json();assert first['ok'] and first['raw_text']==response.json()['raw_text']
            ws.send_bytes(image);second=ws.receive_json();assert second['stable']
    result=dict(scope='In-process HTTP/WebSocket routes with real YOLO model. Optional community translations contact an unofficial service; not quality certification.',recognition=dict(http_status=response.status_code,raw_text=response.json()['raw_text'],detections=response.json()['detections'],websocket_agrees=True,second_frame_stable=second['stable']))
    if args.community: result['community_translation']=asyncio.run(translations())
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
