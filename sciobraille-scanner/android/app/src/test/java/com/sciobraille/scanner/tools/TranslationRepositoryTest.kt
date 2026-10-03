package com.sciobraille.scanner.tools

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test

class TranslationRepositoryTest {
    @Test
    fun scannerTextPassesDirectlyToTamilRequest() {
        val json = JSONObject(TranslationRepository.requestJson("good morning", AppLanguage.TAMIL))
        assertEquals("good morning", json.getString("text"))
        assertEquals("en", json.getString("source_lang"))
        assertEquals("ta", json.getString("target_lang"))
    }

    @Test
    fun targetLanguageCodesAreCentralized() {
        assertEquals("hi", JSONObject(TranslationRepository.requestJson("hello", AppLanguage.HINDI)).getString("target_lang"))
        assertEquals("es", JSONObject(TranslationRepository.requestJson("hello", AppLanguage.SPANISH)).getString("target_lang"))
    }
}
