package com.sciobraille.scanner.tools

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import java.util.UUID

enum class SpeechStatus { SPOKEN, UNAVAILABLE, MISSING_LANGUAGE_DATA, ERROR }
data class SpeechRequest(val text: String, val locale: Locale, val utteranceId: String)
class MultilingualTtsManager(private val context: Context? = null, private val textToSpeechProvider: () -> TextToSpeech?) {
    var speechRate=0.92f
    var pitch=1f
    var preferredVoice=""
    var offlineOnly=false
    private var request: SpeechRequest?=null
    @Volatile private var offset=0
    private var chunkStart=0
    private var chunkEnd=0
    @Volatile private var activeId=""
    @Volatile private var paused=false
    private var focus: AudioFocusRequest?=null
    private val audio get()=context?.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    fun speakOriginal(text: String)=speak(buildOriginalRequest(text))
    fun speakTranslated(text: String, language: AppLanguage)=speak(buildTranslatedRequest(text,language))
    fun pause() { paused=true; activeId=""; textToSpeechProvider()?.stop(); releaseFocus() }
    fun resume(): SpeechStatus = request?.let { speak(it,offset) } ?: SpeechStatus.ERROR
    fun replay(): SpeechStatus = speak(request)
    fun stop() { pause(); request=null; offset=0 }
    private fun speak(value: SpeechRequest?, start: Int=0): SpeechStatus {
        if(value==null) return SpeechStatus.ERROR
        val tts=textToSpeechProvider() ?: return SpeechStatus.UNAVAILABLE
        return runCatching {
            if(tts.isLanguageAvailable(value.locale)<TextToSpeech.LANG_AVAILABLE) return SpeechStatus.MISSING_LANGUAGE_DATA
            val voices=tts.voices.orEmpty().filter { it.locale.language.equals(value.locale.language,true) && (!offlineOnly || !it.isNetworkConnectionRequired) }
                .sortedWith(compareBy<android.speech.tts.Voice> { it.isNetworkConnectionRequired }.thenByDescending { it.locale.toLanguageTag().equals(value.locale.toLanguageTag(),true) }.thenByDescending { it.quality })
            if(offlineOnly && voices.isEmpty()) return SpeechStatus.MISSING_LANGUAGE_DATA
            tts.language=value.locale
            (voices.firstOrNull { it.name==preferredVoice } ?: voices.firstOrNull())?.let { tts.voice=it }
            tts.setSpeechRate(speechRate.coerceIn(.5f,1.5f)); tts.setPitch(pitch.coerceIn(.5f,1.5f))
            val attrs=AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
            tts.setAudioAttributes(attrs); releaseFocus()
            focus=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK).setAudioAttributes(attrs).setOnAudioFocusChangeListener { if(it<0) pause() }.build()
            if(audio?.requestAudioFocus(requireNotNull(focus))==AudioManager.AUDIOFOCUS_REQUEST_FAILED) return SpeechStatus.ERROR
            request=value; offset=start.coerceIn(0,value.text.length); paused=false
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?)=Unit
                override fun onRangeStart(utteranceId: String?, start: Int, end: Int, frame: Int) { if(utteranceId==activeId) offset=chunkStart+start }
                override fun onDone(utteranceId: String?) {
                    if(utteranceId!=activeId || paused) return
                    offset=chunkEnd
                    if(offset<value.text.length) queue(tts,value) else { activeId=""; releaseFocus() }
                }
                @Deprecated("Platform callback")
                override fun onError(utteranceId: String?) { if(utteranceId==activeId) { activeId=""; releaseFocus() } }
            }); queue(tts,value)
        }.getOrElse { releaseFocus(); SpeechStatus.ERROR }
    }
    private fun queue(tts: TextToSpeech,value: SpeechRequest): SpeechStatus {
        if(offset>=value.text.length) offset=0
        chunkStart=offset; chunkEnd=minOf(value.text.length,offset+TextToSpeech.getMaxSpeechInputLength()-1)
        if(chunkEnd<value.text.length && value.text[chunkEnd-1].isHighSurrogate()) chunkEnd--
        activeId=UUID.randomUUID().toString()
        if(tts.speak(value.text.substring(chunkStart,chunkEnd),TextToSpeech.QUEUE_FLUSH,null,activeId)==TextToSpeech.ERROR) { releaseFocus(); return SpeechStatus.ERROR }
        return SpeechStatus.SPOKEN
    }
    private fun releaseFocus() { focus?.let { audio?.abandonAudioFocusRequest(it) }; focus=null }
    companion object {
        fun buildOriginalRequest(text: String): SpeechRequest?=text.trim().takeIf { it.isNotBlank() }?.let { SpeechRequest(it.replace('\n','.'),Locale.forLanguageTag(AppLanguage.ENGLISH.localeTag),"sciobraille-original") }
        fun buildTranslatedRequest(text: String,language: AppLanguage): SpeechRequest?=text.trim().takeIf { it.isNotBlank() }?.let { SpeechRequest(it.replace('\n','.'),Locale.forLanguageTag(language.localeTag),"sciobraille-translation-${language.languageCode}") }
    }
}
