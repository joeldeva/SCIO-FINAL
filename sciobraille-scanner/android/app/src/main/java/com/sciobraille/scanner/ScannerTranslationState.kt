package com.sciobraille.scanner

import com.sciobraille.scanner.tools.AppLanguage

enum class TranslationStatus { IDLE, TRANSLATING, SUCCESS, FAILED, OFFLINE_UNAVAILABLE, UNSUPPORTED }

data class ScannerResultState(
    val rawText: String = "",
    val recognizedText: String = "",
    val correctedText: String = "",
    val translatedText: String = "",
    val selectedLanguage: AppLanguage = AppLanguage.ENGLISH,
    val translatedLanguage: AppLanguage? = null,
    val translationStatus: TranslationStatus = TranslationStatus.IDLE,
    val translationMessage: String = ""
) {
    fun withRecognizedResult(raw: String, recognized: String, corrected: String): ScannerResultState = copy(
        rawText = raw,
        recognizedText = recognized,
        correctedText = corrected,
        translatedText = "",
        translatedLanguage = null,
        translationStatus = TranslationStatus.IDLE,
        translationMessage = ""
    )

    fun selectLanguage(language: AppLanguage): ScannerResultState = copy(selectedLanguage = language)
}
