package com.sciobraille.scanner.tools

import com.sciobraille.scanner.lms.BrailleMappings

enum class BrailleTokenType {
    CELL,
    SPACE,
    LINE_BREAK
}

data class BrailleToken(
    val type: BrailleTokenType,
    val source: Char?,
    val dots: Set<Int>,
    val spokenLabel: String
) {
    val unicode: String
        get() = when (type) {
            BrailleTokenType.CELL -> dotsToUnicode(dots).toString()
            BrailleTokenType.SPACE -> " "
            BrailleTokenType.LINE_BREAK -> "\n"
        }
}

data class Grade1BrailleTranslation(
    val sourceText: String,
    val tokens: List<BrailleToken>,
    val unsupportedCharacters: List<Char>
) {
    val unicodeText: String = tokens.joinToString(separator = "") { it.unicode }
    val cells: List<BrailleToken> = tokens.filter { it.type == BrailleTokenType.CELL }
}

/** Deterministic English Grade 1 encoder used by Studio, tactile playback, and lessons. */
object Grade1BrailleCodec {
    private val digitToLetter = mapOf(
        '1' to 'A', '2' to 'B', '3' to 'C', '4' to 'D', '5' to 'E',
        '6' to 'F', '7' to 'G', '8' to 'H', '9' to 'I', '0' to 'J'
    )

    private val punctuation = mapOf(
        ',' to setOf(2),
        ';' to setOf(2, 3),
        ':' to setOf(2, 5),
        '.' to setOf(2, 5, 6),
        '!' to setOf(2, 3, 5),
        '?' to setOf(2, 3, 6),
        '-' to setOf(3, 6),
        '\'' to setOf(3),
        '"' to setOf(3, 5, 6),
        '/' to setOf(3, 4),
        '(' to setOf(2, 3, 5, 6),
        ')' to setOf(2, 3, 5, 6)
    )

    fun translate(text: String): Grade1BrailleTranslation {
        val tokens = mutableListOf<BrailleToken>()
        val unsupported = mutableListOf<Char>()
        var numberMode = false

        text.forEach { character ->
            when {
                character == '\n' -> {
                    tokens += BrailleToken(BrailleTokenType.LINE_BREAK, character, emptySet(), "new line")
                    numberMode = false
                }
                character.isWhitespace() -> {
                    tokens += BrailleToken(BrailleTokenType.SPACE, character, emptySet(), "space")
                    numberMode = false
                }
                character.isDigit() -> {
                    if (!numberMode) {
                        tokens += cell(null, setOf(3, 4, 5, 6), "number indicator")
                        numberMode = true
                    }
                    val letter = digitToLetter.getValue(character)
                    tokens += cell(character, BrailleMappings.getDotsForLetter(letter), "number $character")
                }
                character.isLetter() && character.uppercaseChar() in BrailleMappings.letterToDots -> {
                    numberMode = false
                    if (character.isUpperCase()) {
                        tokens += cell(null, setOf(6), "capital indicator")
                    }
                    val letter = character.uppercaseChar()
                    tokens += cell(character, BrailleMappings.getDotsForLetter(letter), "letter $letter")
                }
                punctuation.containsKey(character) -> {
                    numberMode = false
                    tokens += cell(character, punctuation.getValue(character), punctuationName(character))
                }
                else -> {
                    numberMode = false
                    unsupported += character
                }
            }
        }

        return Grade1BrailleTranslation(text, tokens, unsupported.distinct())
    }

    private fun cell(source: Char?, dots: Set<Int>, label: String) = BrailleToken(
        type = BrailleTokenType.CELL,
        source = source,
        dots = dots,
        spokenLabel = label
    )

    private fun punctuationName(character: Char): String = when (character) {
        ',' -> "comma"
        ';' -> "semicolon"
        ':' -> "colon"
        '.' -> "period"
        '!' -> "exclamation mark"
        '?' -> "question mark"
        '-' -> "hyphen"
        '\'' -> "apostrophe"
        '"' -> "quotation mark"
        '/' -> "slash"
        '(' -> "opening parenthesis"
        ')' -> "closing parenthesis"
        else -> character.toString()
    }
}

fun dotsToUnicode(dots: Set<Int>): Char {
    val bitMask = dots.fold(0) { mask, dot ->
        if (dot in 1..8) mask or (1 shl (dot - 1)) else mask
    }
    return (0x2800 + bitMask).toChar()
}
