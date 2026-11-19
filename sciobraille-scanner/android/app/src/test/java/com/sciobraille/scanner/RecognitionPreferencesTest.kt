package com.sciobraille.scanner

import org.junit.Assert.assertEquals
import org.junit.Test

class RecognitionPreferencesTest {
    @Test
    fun orientationCandidatesMatchSelectedMode() {
        assertEquals(listOf(true, false), OfflineOrientationPolicy.candidates(ScanSideMode.AUTOMATIC))
        assertEquals(listOf(false), OfflineOrientationPolicy.candidates(ScanSideMode.FRONT_ONLY))
        assertEquals(listOf(true), OfflineOrientationPolicy.candidates(ScanSideMode.REVERSE_ONLY))
    }

    @Test
    fun unknownStoredModeFallsBackToAutomatic() {
        assertEquals(ScanSideMode.AUTOMATIC, ScanSideMode.fromStored("UNKNOWN"))
    }
}
