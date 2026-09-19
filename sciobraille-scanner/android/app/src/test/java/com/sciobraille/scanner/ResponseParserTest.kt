package com.sciobraille.scanner

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ResponseParserTest {
    @Test
    fun parsesScannerPayload() {
        val payload = ScannerPayload.fromJson(
            """{"ok":true,"text":"jaihind\nindia","raw_text":"jaihfind\nindia","corrected_text":"jaihind\nindia","stable":true,"detections":12,"confidence":0.82}"""
        )

        assertTrue(payload.ok)
        assertTrue(payload.stable)
        assertEquals("jaihind\nindia", payload.text)
        assertEquals("jaihfind\nindia", payload.rawText)
        assertEquals("jaihind\nindia", payload.correctedText)
        assertEquals(12, payload.detections)
        assertEquals(0.82, payload.confidence, 0.001)
    }

    @Test
    fun malformedScannerPayloadReturnsNull() {
        assertNull(ScannerPayload.fromJsonOrNull("not-json"))
    }
}
