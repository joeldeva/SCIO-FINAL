package com.sciobraille.scanner

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ScannerInputPolicyTest {
    @Test
    fun productionScannerAlwaysRequestsHorizontalFlip() {
        assertTrue(ScannerInputPolicy.FORCE_HORIZONTAL_FLIP)
        assertEquals("/ws/scan?flip_horizontal=true", ScannerInputPolicy.webSocketPath())
        assertEquals("/api/scan-frame?flip_horizontal=true", ScannerInputPolicy.uploadPath())
    }
}
