package com.sciobraille.scanner.lms

object BrailleMappings {
    val letterToDots: Map<Char, Set<Int>> = linkedMapOf(
        'A' to setOf(1),
        'B' to setOf(1, 2),
        'C' to setOf(1, 4),
        'D' to setOf(1, 4, 5),
        'E' to setOf(1, 5),
        'F' to setOf(1, 2, 4),
        'G' to setOf(1, 2, 4, 5),
        'H' to setOf(1, 2, 5),
        'I' to setOf(2, 4),
        'J' to setOf(2, 4, 5),
        'K' to setOf(1, 3),
        'L' to setOf(1, 2, 3),
        'M' to setOf(1, 3, 4),
        'N' to setOf(1, 3, 4, 5),
        'O' to setOf(1, 3, 5),
        'P' to setOf(1, 2, 3, 4),
        'Q' to setOf(1, 2, 3, 4, 5),
        'R' to setOf(1, 2, 3, 5),
        'S' to setOf(2, 3, 4),
        'T' to setOf(2, 3, 4, 5),
        'U' to setOf(1, 3, 6),
        'V' to setOf(1, 2, 3, 6),
        'W' to setOf(2, 4, 5, 6),
        'X' to setOf(1, 3, 4, 6),
        'Y' to setOf(1, 3, 4, 5, 6),
        'Z' to setOf(1, 3, 5, 6)
    )

    val dotPatternToLetter: Map<Set<Int>, Char> = letterToDots.entries.associate { (letter, dots) ->
        dots to letter
    }

    fun getDotsForLetter(letter: Char): Set<Int> {
        return letterToDots[letter.uppercaseChar()].orEmpty()
    }

    fun getLetterForDots(dots: Set<Int>): Char? {
        return dotPatternToLetter[dots.toSet()]
    }

    fun getDotPositionDescription(dot: Int): String {
        return when (dot) {
            1 -> "left column, top row"
            2 -> "left column, middle row"
            3 -> "left column, bottom row"
            4 -> "right column, top row"
            5 -> "right column, middle row"
            6 -> "right column, bottom row"
            else -> "unknown position"
        }
    }

    fun getDotPatternsForWord(word: String): List<Set<Int>> {
        return word.mapNotNull { char ->
            if (char.isLetter()) getDotsForLetter(char).takeIf { it.isNotEmpty() } else null
        }
    }
}
