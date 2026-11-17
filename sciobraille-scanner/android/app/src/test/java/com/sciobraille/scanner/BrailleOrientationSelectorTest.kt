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

    @Test
    fun flippedEmbossedCandidateWinsWhenItHasBetterConfidenceAndText() {
        assertTrue(
            !BrailleOrientationSelector.preferAlternate(
                primaryText = "ssn invente",
                primaryDetections = 10,
                primaryConfidence = 0.70,
                alternateText = "iie",
                alternateDetections = 3,
                alternateConfidence = 0.63
            )
        )
    }

    @Test
    fun naturalFrontSideCandidateCanReplaceGibberish() {
        assertTrue(
            BrailleOrientationSelector.preferAlternate(
                primaryText = "f djeah ee eawb ec we p e lausi cih w aerg",
                primaryDetections = 31,
                primaryConfidence = 0.54,
                alternateText = "jaihf d india sciobraille visually impaired greaq project",
                alternateDetections = 50,
                alternateConfidence = 0.80
            )
        )
    }
}
