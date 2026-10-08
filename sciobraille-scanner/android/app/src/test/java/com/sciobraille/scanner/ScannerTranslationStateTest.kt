package com.sciobraille.scanner

import com.sciobraille.scanner.tools.AppLanguage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ScannerTranslationStateTest {
    @Test
    fun selectingLanguagePreservesExistingTranslationAndSource() {
        val state = ScannerResultState(
            rawText = "raw",
            recognizedText = "hello",
            correctedText = "hello",
            translatedText = "नमस्ते",
            selectedLanguage = AppLanguage.HINDI,
            translatedLanguage = AppLanguage.HINDI,
            translationStatus = TranslationStatus.SUCCESS
        ).selectLanguage(AppLanguage.TAMIL)

        assertEquals("raw", state.rawText)
        assertEquals("hello", state.recognizedText)
        assertEquals("नमस्ते", state.translatedText)
        assertEquals(AppLanguage.TAMIL, state.selectedLanguage)
        assertEquals(AppLanguage.HINDI, state.translatedLanguage)
    }

    @Test
    fun newRecognitionClearsOnlyOldTranslation() {
        val state = ScannerResultState(translatedText = "old").withRecognizedResult("raw", "recognized", "corrected")
        assertEquals("raw", state.rawText)
        assertEquals("recognized", state.recognizedText)
        assertEquals("corrected", state.correctedText)
        assertTrue(state.translatedText.isEmpty())
    }
}
