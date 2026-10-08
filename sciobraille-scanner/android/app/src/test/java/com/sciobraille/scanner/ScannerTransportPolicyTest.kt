package com.sciobraille.scanner

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScannerTransportPolicyTest {
    @Test
    fun connectingSocketDoesNotBlockOfflineInference() {
        assertFalse(ScannerTransportPolicy.canSendToBackend(false, true))
    }

    @Test
    fun openSocketCanReceiveFrames() {
        assertTrue(ScannerTransportPolicy.canSendToBackend(true, true))
    }

    @Test
    fun missingSocketUsesOfflineInference() {
        assertFalse(ScannerTransportPolicy.canSendToBackend(true, false))
    }
}
