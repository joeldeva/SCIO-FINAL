package com.sciobraille.scanner.lms

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LmsProgressRulesTest {
    @Test
    fun calculatesProgressAndLevelCompletion() {
        assertEquals(50, LmsProgressRules.completionPercent(5, 10))
        assertEquals(100, LmsProgressRules.completionPercent(12, 10))
        assertTrue(LmsProgressRules.isLevelComplete(10, 10, 70f, 75f))
        assertFalse(LmsProgressRules.isLevelComplete(10, 10, 70f, 65f))
    }

    @Test
    fun appliesFreeAndPremiumUnlockRules() {
        assertTrue(LmsProgressRules.canUnlockLetterBuilder(true))
        assertFalse(LmsProgressRules.canUnlockRecognition(false, 4, true))
        assertTrue(LmsProgressRules.canUnlockRecognition(false, 5, true))
        assertFalse(LmsProgressRules.canUnlockRecognition(false, 5, false))
        assertTrue(LmsProgressRules.canUnlockRecognition(true, 10, false))
        assertFalse(LmsProgressRules.canUnlockPremiumLevel(false, true))
        assertTrue(LmsProgressRules.canUnlockPremiumLevel(true, true))
    }
}
