package com.sciobraille.scanner.tools

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MultilingualTtsManagerTest {
    @Test
    fun translatedSpeechUsesTranslatedTextAndTargetLocale() {
        val request = MultilingualTtsManager.buildTranslatedRequest("காலை வணக்கம்", AppLanguage.TAMIL)!!
        assertEquals("காலை வணக்கம்", request.text)
        assertEquals("ta-IN", request.locale.toLanguageTag())
    }

    @Test
    fun originalSpeechUsesRecognizedTextAndEnglishLocale() {
        val request = MultilingualTtsManager.buildOriginalRequest("good morning")!!
        assertEquals("good morning", request.text)
        assertEquals("en-IN", request.locale.toLanguageTag())
    }

    @Test
    fun emptyTextCannotCreateSpeechRequest() {
        assertNull(MultilingualTtsManager.buildOriginalRequest("  "))
        assertNull(MultilingualTtsManager.buildTranslatedRequest("", AppLanguage.HINDI))
    }
}
