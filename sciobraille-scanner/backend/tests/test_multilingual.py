import asyncio
from collections import deque
from unittest.mock import patch
import httpx
import pytest
from fastapi.testclient import TestClient
import scanner_api
from translation_service import TranslationService, TranslationError
from reading_order import aligned_centers

def run(value): return asyncio.run(value)

def test_google_unicode_and_auto_source():
    requests=[]
    def handler(request):
        requests.append(request)
        if request.method=='GET': return httpx.Response(200,json={'data':{'languages':[{'language':'ta','name':'Tamil'}]}})
        return httpx.Response(200,json={'data':{'translations':[{'translatedText':'வணக்கம்!','detectedSourceLanguage':'en'}]}})
    service=TranslationService('google',httpx.MockTransport(handler));service.api_key='test-only'
    value=run(service.translate('Welcome!','auto','ta'))
    assert value.text=='வணக்கம்!' and value.detected_source=='en'
    assert b'"source"' not in requests[-1].content
    assert requests[-1].headers['X-Goog-Api-Key']=='test-only'

def test_libre_only_english_pairs_are_advertised():
    data=[{'code':'en','name':'English','targets':['fr']},{'code':'fr','name':'French','targets':['en']},{'code':'ja','name':'Japanese','targets':['ko']}]
    service=TranslationService('libretranslate',httpx.MockTransport(lambda _: httpx.Response(200,json=data)))
    assert run(service.languages())=={'en':'English','fr':'French'}

@pytest.mark.parametrize('response',[httpx.Response(500),httpx.Response(200,json={'translatedText':''})])
def test_provider_failures_never_return_source_as_translation(response):
    service=TranslationService('libretranslate',httpx.MockTransport(lambda _: response));service._languages={'ta':'Tamil'};service._expires=float('inf')
    with pytest.raises(TranslationError): run(service.translate('hello','en','ta'))

def test_provider_timeout_is_reported():
    def handler(_): raise httpx.ReadTimeout('timeout')
    service=TranslationService('libretranslate',httpx.MockTransport(handler));service._languages={'ta':'Tamil'};service._expires=float('inf')
    with pytest.raises(TranslationError) as error: run(service.translate('hello','en','ta'))
    assert error.value.status_code==504

def test_disabled_languages_and_no_public_lms():
    with TestClient(scanner_api.app) as client, patch.object(scanner_api,'translation_service',TranslationService('disabled')):
        assert client.get('/api/languages').json()['languages']==[{'code':'en','name':'English'}]
        assert client.get('/api/schools').status_code==404
        assert not client.get('/api/capabilities').json()['recognition_systems'][1]['enabled']

def test_translation_strict_input_bounds():
    with TestClient(scanner_api.app) as client:
        for body in [{'text':{}},{'text':[]},{'text':'abc','target_lang':1}]: assert client.post('/api/translate',json=body).status_code==400
        assert client.post('/api/translate',json={'text':'a'*4001}).status_code==413
        assert client.post('/api/translate',content=b' '*32001).status_code==413

def test_blank_frame_resets_stability():
    history=deque(maxlen=5)
    scanner_api._stabilize_text('abc',history);scanner_api._stabilize_text('abc',history)
    assert scanner_api._stabilize_text('',history)==('',False)
    assert not scanner_api._stabilize_text('xyz',history)[1]

def test_consistent_mild_skew_is_aligned_without_mutating_boxes():
    boxes=[dict(x_center=x,y_center=20+x*.2,height=20) for x in [0,20,40,60,80]]
    aligned=aligned_centers(boxes)
    assert max(x['y_center'] for x in aligned)-min(x['y_center'] for x in aligned)<1e-6
    assert boxes[-1]['y_center']==36
