package com.sciobraille.scanner.lms

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BrailleMappingsTest {
    @Test
    fun mapsAllEnglishLettersToGradeOneDots() {
        assertEquals(26, BrailleMappings.letterToDots.size)
        assertEquals(setOf(1), BrailleMappings.getDotsForLetter('A'))
        assertEquals(setOf(1, 2, 4, 5), BrailleMappings.getDotsForLetter('g'))
        assertEquals(setOf(2, 4, 5, 6), BrailleMappings.getDotsForLetter('W'))
        assertEquals(setOf(1, 3, 5, 6), BrailleMappings.getDotsForLetter('z'))
    }

    @Test
    fun mapsDotPatternsBackToLetters() {
        assertEquals('A', BrailleMappings.getLetterForDots(setOf(1)))
        assertEquals('T', BrailleMappings.getLetterForDots(setOf(2, 3, 4, 5)))
        assertEquals('Y', BrailleMappings.getLetterForDots(setOf(1, 3, 4, 5, 6)))
        assertNull(BrailleMappings.getLetterForDots(setOf(6)))
    }

    @Test
    fun mapsWordsToDotPatterns() {
        assertEquals(
            listOf(setOf(1, 4), setOf(1), setOf(2, 3, 4, 5)),
            BrailleMappings.getDotPatternsForWord("cat")
        )
    }

    @Test
    fun describesDotPositions() {
        assertEquals("left column, top row", BrailleMappings.getDotPositionDescription(1))
        assertEquals("right column, bottom row", BrailleMappings.getDotPositionDescription(6))
    }
}
