package com.sciobraille.scanner.tools

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Grade1BrailleCodecTest {
    @Test
    fun translatesLettersCapitalsNumbersAndPunctuation() {
        val translation = Grade1BrailleCodec.translate("A 10!")

        assertEquals(
            listOf(
                setOf(6),
                setOf(1),
                setOf(3, 4, 5, 6),
                setOf(1),
                setOf(2, 4, 5),
                setOf(2, 3, 5)
            ),
            translation.cells.map { it.dots }
        )
        assertTrue(translation.unsupportedCharacters.isEmpty())
    }

    @Test
    fun reportsUnsupportedCharactersWithoutInventingPatterns() {
        val translation = Grade1BrailleCodec.translate("cat@")

        assertEquals(3, translation.cells.size)
        assertEquals(listOf('@'), translation.unsupportedCharacters)
    }

    @Test
    fun preservesSpacesAndLineBreaksInUnicodeOutput() {
        val translation = Grade1BrailleCodec.translate("a b\nc")

        assertEquals("${dotsToUnicode(setOf(1))} ${dotsToUnicode(setOf(1, 2))}\n${dotsToUnicode(setOf(1, 4))}", translation.unicodeText)
    }
}
