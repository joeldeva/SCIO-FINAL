# Multilingual Translation and Speech Report

## Architecture

Braille detection and spatial reconstruction still produce English text. Android stores raw, recognized, corrected, and translated values separately. `TranslationRepository` sends recognized English text to the existing FastAPI `/api/translate` endpoint. `MultilingualTtsManager` reuses the application's single `TextToSpeech` engine and speaks translated text only with the matching target locale.

## Supported languages

- English: `en-IN`
- Hindi: `hi-IN`
- Tamil: `ta-IN`
- Telugu: `te-IN`
- Malayalam: `ml-IN`
- Kannada: `kn-IN`
- Spanish: `es-ES`
- French: `fr-FR`
- German: `de-DE`
- Chinese: `zh-CN`
- Japanese: `ja-JP`

## Behavior

- Scanner translation uses `recognizedText`; it never overwrites `rawText`.
- Original and translated speech have separate controls.
- Changing target language preserves the last translation until a new translation succeeds.
- Translation failure preserves original output and shows an accessible error.
- Missing TTS voice data opens an optional Android voice installation action.
- Auto-speak scan and auto-speak translation are off by default and saved locally.
- History remains backward-compatible and stores translation, language, orientation, mode, confidence, and timestamp when available.
- Smart Assist accepts commands such as `Translate to Tamil`, `Speak in Hindi`, and `Speak translation`.

## Translation source and fallback

Primary source is the existing FastAPI endpoint backed by `deep-translator`. Source language is explicitly English. If the backend is unavailable, rate-limited, or returns an error, Android uses Google ML Kit Translation. ML Kit downloads a supported language model before first local use and then supports offline translation. Unsupported or unavailable models produce a clear error and preserve original text.

## Verification

- Backend: `31 passed`.
- Android JVM tests: `35 passed`.
- Android debug build: successful.
- Automated tests verify centralized language codes, English-to-Tamil/Hindi/Spanish requests, source preservation, empty input handling, and target-locale TTS requests.

## Physical-device limitations

Locale selection is automated and tested. Speech quality and availability still depend on installed TTS engine and language voice packs. Each supported voice must be manually verified on the target phone. First ML Kit use requires internet to download each selected language model.
