package com.sciobraille.scanner.tools

import android.speech.tts.TextToSpeech
import java.util.Locale

enum class SpeechStatus { SPOKEN, UNAVAILABLE, MISSING_LANGUAGE_DATA, ERROR }

data class SpeechRequest(val text: String, val locale: Locale, val utteranceId: String)

class MultilingualTtsManager(
    private val textToSpeechProvider: () -> TextToSpeech?
) {
    var speechRate: Float = 0.92f
    var pitch: Float = 1f

    fun speakOriginal(recognizedText: String): SpeechStatus =
        speak(buildOriginalRequest(recognizedText))

    fun speakTranslated(translatedText: String, language: AppLanguage): SpeechStatus =
        speak(buildTranslatedRequest(translatedText, language))

    fun stop() {
        runCatching { textToSpeechProvider()?.stop() }
    }

    private fun speak(request: SpeechRequest?): SpeechStatus {
        if (request == null) return SpeechStatus.ERROR
        val tts = textToSpeechProvider() ?: return SpeechStatus.UNAVAILABLE
        return runCatching {
            val availability = tts.isLanguageAvailable(request.locale)
            if (availability < TextToSpeech.LANG_AVAILABLE) return SpeechStatus.MISSING_LANGUAGE_DATA
            val voices = tts.voices.orEmpty().filter { it.locale != null }
            val exact = voices.firstOrNull { it.locale.toLanguageTag().equals(request.locale.toLanguageTag(), true) }
            val family = voices.firstOrNull { it.locale.language.equals(request.locale.language, true) }
            (exact ?: family)?.let { tts.voice = it }
            tts.language = request.locale
            tts.setSpeechRate(speechRate.coerceIn(0.5f, 1.5f))
            tts.setPitch(pitch.coerceIn(0.5f, 1.5f))
            if (tts.speak(request.text, TextToSpeech.QUEUE_FLUSH, null, request.utteranceId) == TextToSpeech.ERROR) {
                SpeechStatus.ERROR
            } else SpeechStatus.SPOKEN
        }.getOrElse { SpeechStatus.ERROR }
    }

    companion object {
        fun buildOriginalRequest(text: String): SpeechRequest? = text.trim().takeIf { it.isNotBlank() }?.let {
            SpeechRequest(it.replace('\n', '.'), Locale.forLanguageTag(AppLanguage.ENGLISH.localeTag), "sciobraille-original")
        }

        fun buildTranslatedRequest(text: String, language: AppLanguage): SpeechRequest? =
            text.trim().takeIf { it.isNotBlank() }?.let {
                SpeechRequest(it.replace('\n', '.'), Locale.forLanguageTag(language.localeTag), "sciobraille-translation-${language.languageCode}")
            }
    }
}
