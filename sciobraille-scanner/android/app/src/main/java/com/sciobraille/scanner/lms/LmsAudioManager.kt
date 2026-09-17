package com.sciobraille.scanner.lms

import android.speech.tts.TextToSpeech
import java.util.Locale

class LmsAudioManager(
    private val textToSpeechProvider: () -> TextToSpeech?
) {
    var autoSpeakEnabled: Boolean = true
        private set

    private var lastSpokenText: String = ""

    fun configureDefaults() {
        runCatching {
            textToSpeechProvider()?.apply {
                language = Locale.US
                setSpeechRate(0.92f)
            }
        }
    }

    fun setAutoSpeak(enabled: Boolean) {
        autoSpeakEnabled = enabled
        if (!enabled) stop()
    }

    fun toggleAutoSpeak(): Boolean {
        setAutoSpeak(!autoSpeakEnabled)
        return autoSpeakEnabled
    }

    fun speak(text: String) {
        speakInternal(text, respectAutoSpeak = true)
    }

    fun repeatLast() {
        speakInternal(lastSpokenText, respectAutoSpeak = false)
    }

    fun speakDot(dot: Int) {
        speak("This is dot $dot, ${BrailleMappings.getDotPositionDescription(dot)}.")
    }

    fun speakLetter(letter: Char, dots: Set<Int>) {
        speak("Letter ${letter.uppercaseChar()} uses ${dotPhrase(dots)}.")
    }

    fun speakWord(word: String) {
        val cleanWord = word.trim()
        if (cleanWord.isBlank()) return
        speak("The word is $cleanWord. It has ${cleanWord.length} ${if (cleanWord.length == 1) "letter" else "letters"}.")
    }

    fun speakCorrect(message: String) {
        speak(message)
    }

    fun speakIncorrect(message: String) {
        speak(message)
    }

    fun stop() {
        runCatching { textToSpeechProvider()?.stop() }
    }

    private fun speakInternal(text: String, respectAutoSpeak: Boolean) {
        val cleaned = text.trim()
        if (cleaned.isBlank()) return
        lastSpokenText = cleaned
        if (respectAutoSpeak && !autoSpeakEnabled) return
        runCatching {
            textToSpeechProvider()?.let { tts ->
                tts.stop()
                tts.speak(cleaned, TextToSpeech.QUEUE_FLUSH, null, "sciobraille-lms")
            }
        }
    }

    private fun dotPhrase(dots: Set<Int>): String {
        val sorted = dots.sorted()
        return when (sorted.size) {
            0 -> "no dots"
            1 -> "dot ${sorted.first()} only"
            2 -> "dots ${sorted[0]} and ${sorted[1]}"
            else -> "dots ${sorted.dropLast(1).joinToString(", ")}, and ${sorted.last()}"
        }
    }
}
