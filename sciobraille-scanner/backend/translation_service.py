"""Server-side provider adapters; credentials never enter the Android app."""
import asyncio
import html
import os
import time
from dataclasses import dataclass
import httpx

class TranslationError(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code

@dataclass(frozen=True)
class Translation:
    text: str
    detected_source: str | None = None

class TranslationService:
    def __init__(self, provider=None, transport=None):
        self.provider = provider or os.getenv('TRANSLATION_PROVIDER', 'disabled')
        self.api_key = os.getenv('TRANSLATION_API_KEY', '')
        self.base_url = os.getenv('LIBRETRANSLATE_URL', 'http://127.0.0.1:5000').rstrip('/')
        self.transport = transport
        self._languages = {}
        self._expires = 0
        self._lock = asyncio.Lock()
        self._slots = asyncio.Semaphore(4)

    def _client(self):
        return httpx.AsyncClient(timeout=httpx.Timeout(12, connect=4), transport=self.transport)

    async def languages(self):
        if self._languages and time.monotonic() < self._expires: return dict(self._languages)
        async with self._lock:
            try:
                if self.provider == 'disabled': result = {'en':'English'}
                elif self.provider == 'community':
                    from deep_translator import GoogleTranslator
                    result = {v:k.title() for k,v in GoogleTranslator().get_supported_languages(as_dict=True).items()}
                elif self.provider == 'google':
                    if not self.api_key: raise TranslationError('Online translation is not configured')
                    async with self._client() as client:
                        response = await client.get('https://translation.googleapis.com/language/translate/v2/languages', params={'target':'en'}, headers={'X-Goog-Api-Key':self.api_key})
                        response.raise_for_status()
                        result = {x['language']:x['name'] for x in response.json()['data']['languages']}
                elif self.provider == 'libretranslate':
                    async with self._client() as client:
                        response = await client.get(self.base_url+'/languages')
                        response.raise_for_status()
                        items = response.json()
                        targets = set(next((x for x in items if x['code']=='en'), {}).get('targets',[])) | {'en'}
                        result = {x['code']:x['name'] for x in items if x['code'] in targets}
                else: raise TranslationError('Unknown translation provider')
                self._languages, self._expires = result, time.monotonic()+3600
                return dict(result)
            except TranslationError: raise
            except Exception as exc: raise TranslationError('Online language availability could not be checked') from exc

    async def translate(self, text, source, target):
        if source == target: return Translation(text, source)
        if self.provider == 'disabled': raise TranslationError('Online translation is disabled')
        if target not in await self.languages(): raise TranslationError('Unsupported translation language',400)
        try:
            async with self._slots:
                if self.provider == 'community':
                    # Opt-in legacy adapter, for evaluation only; no SLA.
                    from deep_translator import GoogleTranslator
                    result = Translation(await asyncio.wait_for(asyncio.to_thread(GoogleTranslator(source=source,target=target).translate,text),15) or '')
                else:
                    async with self._client() as client:
                        if self.provider == 'google':
                            body = {'q':text,'target':target,'format':'text'}
                            if source != 'auto': body['source'] = source
                            response = await client.post('https://translation.googleapis.com/language/translate/v2',json=body,headers={'X-Goog-Api-Key':self.api_key})
                            response.raise_for_status()
                            item=response.json()['data']['translations'][0]
                            result=Translation(html.unescape(item['translatedText']),item.get('detectedSourceLanguage'))
                        else:
                            body={'q':text,'source':source,'target':target,'format':'text'}
                            if self.api_key: body['api_key']=self.api_key
                            response=await client.post(self.base_url+'/translate',json=body)
                            response.raise_for_status()
                            item=response.json()
                            result=Translation(item['translatedText'],item.get('detectedLanguage',{}).get('language'))
                if not isinstance(result.text,str) or not result.text.strip(): raise TranslationError('Provider returned empty text',502)
                return result
        except TranslationError: raise
        except (httpx.TimeoutException,asyncio.TimeoutError) as exc: raise TranslationError('Translation timed out. Please retry.',504) from exc
        except Exception as exc: raise TranslationError('Translation unavailable. Original text is preserved.',502) from exc

service=TranslationService()
