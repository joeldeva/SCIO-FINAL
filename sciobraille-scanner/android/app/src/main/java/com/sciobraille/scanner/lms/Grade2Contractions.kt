package com.sciobraille.scanner.lms

data class Grade2Contraction(
    val id: String,
    val contractionText: String,
    val displaySymbol: String,
    val cells: List<Set<Int>>,
    val meaning: String,
    val exampleSentence: String,
    val grade: Int,
    val orderIndex: Int
) {
    val dots: Set<Int>
        get() = cells.firstOrNull().orEmpty()
}

object Grade2Contractions {
    val initialSet: List<Grade2Contraction> = listOf(
        Grade2Contraction(
            id = "the",
            contractionText = "the",
            displaySymbol = "dots 2-3-4-6",
            cells = listOf(setOf(2, 3, 4, 6)),
            meaning = "the word the",
            exampleSentence = "The book is ready.",
            grade = 2,
            orderIndex = 1
        ),
        Grade2Contraction(
            id = "and",
            contractionText = "and",
            displaySymbol = "dots 1-2-3-4-6",
            cells = listOf(setOf(1, 2, 3, 4, 6)),
            meaning = "the word and",
            exampleSentence = "Read and learn.",
            grade = 2,
            orderIndex = 2
        ),
        Grade2Contraction(
            id = "for",
            contractionText = "for",
            displaySymbol = "dots 1-2-3-4-5-6",
            cells = listOf(setOf(1, 2, 3, 4, 5, 6)),
            meaning = "the word for",
            exampleSentence = "This lesson is for practice.",
            grade = 2,
            orderIndex = 3
        ),
        Grade2Contraction(
            id = "of",
            contractionText = "of",
            displaySymbol = "dots 1-2-3-5-6",
            cells = listOf(setOf(1, 2, 3, 5, 6)),
            meaning = "the word of",
            exampleSentence = "A page of Braille.",
            grade = 2,
            orderIndex = 4
        ),
        Grade2Contraction(
            id = "with",
            contractionText = "with",
            displaySymbol = "dots 2-3-4-5-6",
            cells = listOf(setOf(2, 3, 4, 5, 6)),
            meaning = "the word with",
            exampleSentence = "Practice with audio.",
            grade = 2,
            orderIndex = 5
        ),
        Grade2Contraction(
            id = "child",
            contractionText = "child",
            displaySymbol = "dots 1-6",
            cells = listOf(setOf(1, 6)),
            meaning = "the word child",
            exampleSentence = "The child reads Braille.",
            grade = 2,
            orderIndex = 6
        ),
        Grade2Contraction(
            id = "shall",
            contractionText = "shall",
            displaySymbol = "dots 1-4-6",
            cells = listOf(setOf(1, 4, 6)),
            meaning = "the word shall",
            exampleSentence = "We shall keep learning.",
            grade = 2,
            orderIndex = 7
        ),
        Grade2Contraction(
            id = "this",
            contractionText = "this",
            displaySymbol = "dots 1-4-5-6",
            cells = listOf(setOf(1, 4, 5, 6)),
            meaning = "the word this",
            exampleSentence = "This cell is common.",
            grade = 2,
            orderIndex = 8
        ),
        Grade2Contraction(
            id = "which",
            contractionText = "which",
            displaySymbol = "dots 1-5-6",
            cells = listOf(setOf(1, 5, 6)),
            meaning = "the word which",
            exampleSentence = "Which word is shown?",
            grade = 2,
            orderIndex = 9
        ),
        Grade2Contraction(
            id = "out",
            contractionText = "out",
            displaySymbol = "dots 1-2-5-6",
            cells = listOf(setOf(1, 2, 5, 6)),
            meaning = "the word out",
            exampleSentence = "Sound out the word.",
            grade = 2,
            orderIndex = 10
        ),
        Grade2Contraction(
            id = "still",
            contractionText = "still",
            displaySymbol = "dots 3-4",
            cells = listOf(setOf(3, 4)),
            meaning = "the word still",
            exampleSentence = "Keep still while scanning.",
            grade = 2,
            orderIndex = 11
        )
    )

    fun byId(id: String): Grade2Contraction? {
        return initialSet.firstOrNull { it.id == id }
    }

    fun byText(text: String): Grade2Contraction? {
        return initialSet.firstOrNull { it.contractionText.equals(text, ignoreCase = true) }
    }
}
