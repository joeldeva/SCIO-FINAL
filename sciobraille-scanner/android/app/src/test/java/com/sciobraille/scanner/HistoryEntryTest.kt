package com.sciobraille.scanner

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class HistoryEntryTest {
    @Test
    fun oldHistoryLoadsWithoutTranslationFields() {
        val entry = HistoryEntry.fromJson(JSONObject("""{"text":"hello","braille":"x","detections":5,"confidence":0.8,"createdAt":1}"""))
        assertEquals("hello", entry.rawText)
        assertEquals("hello", entry.correctedText)
        assertTrue(entry.translatedText.isEmpty())
        assertEquals("backend", entry.mode)
    }

    @Test
    fun translatedHistoryRoundTrips() {
        val original = HistoryEntry(
            text = "hello",
            braille = "x",
            detections = 5,
            confidence = 0.8,
            createdAt = 1,
            translatedText = "नमस्ते",
            translatedLanguageCode = "hi"
        )
        assertEquals(original, HistoryEntry.fromJson(original.toJson()))
    }
}
