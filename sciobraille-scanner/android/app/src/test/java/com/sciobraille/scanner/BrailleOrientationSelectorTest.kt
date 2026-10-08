package com.sciobraille.scanner

import org.junit.Assert.assertTrue
import org.junit.Test

class BrailleOrientationSelectorTest {
    @Test
    fun normalEnglishOrderScoresAboveMirroredOrder() {
        assertTrue(
            BrailleOrientationSelector.score("ss invente") >
                BrailleOrientationSelector.score("etnevni ss")
        )
    }
}
