package com.sciobraille.scanner.lms

object LmsCurriculumProvider {
    private val gradeOneDots = linkedMapOf(
        "A" to listOf(1),
        "B" to listOf(1, 2),
        "C" to listOf(1, 4),
        "D" to listOf(1, 4, 5),
        "E" to listOf(1, 5),
        "F" to listOf(1, 2, 4),
        "G" to listOf(1, 2, 4, 5),
        "H" to listOf(1, 2, 5),
        "I" to listOf(2, 4),
        "J" to listOf(2, 4, 5),
        "K" to listOf(1, 3),
        "L" to listOf(1, 2, 3),
        "M" to listOf(1, 3, 4),
        "N" to listOf(1, 3, 4, 5),
        "O" to listOf(1, 3, 5),
        "P" to listOf(1, 2, 3, 4),
        "Q" to listOf(1, 2, 3, 4, 5),
        "R" to listOf(1, 2, 3, 5),
        "S" to listOf(2, 3, 4),
        "T" to listOf(2, 3, 4, 5),
        "U" to listOf(1, 3, 6),
        "V" to listOf(1, 2, 3, 6),
        "W" to listOf(2, 4, 5, 6),
        "X" to listOf(1, 3, 4, 6),
        "Y" to listOf(1, 3, 4, 5, 6),
        "Z" to listOf(1, 3, 5, 6)
    )

    private val simpleWords = listOf("cat", "dog", "big", "sun", "cup", "bus", "pen", "fan", "mat", "run")

    fun defaultLessons(): List<LessonEntity> {
        val lessons = mutableListOf<LessonEntity>()
        lessons += dotExplorerLesson()
        lessons += letterBuilderLessons()
        lessons += recognitionLessons()
        lessons += wordReadingLessons()
        lessons += contractionLessons()
        lessons += scanAndLearnLessons()
        lessons += comingSoonLanguageLessons()
        return lessons
    }

    private fun comingSoonLanguageLessons(): List<LessonEntity> = listOf(
        Language.HINDI,
        Language.TAMIL,
        Language.KANNADA
    ).map { language ->
        LessonEntity(
            id = "${language.code}-curriculum-coming-soon",
            level = 1,
            title = "${language.displayName} curriculum",
            description = "This language curriculum is coming soon.",
            contentJson = LessonContent(
                type = "coming_soon",
                goal = "This language curriculum is coming soon."
            ).toJson(),
            orderIndex = 0,
            isPremium = false,
            languageCode = language.code
        )
    }

    private fun dotExplorerLesson(): LessonEntity {
        return LessonEntity(
            id = "level-1-dot-explorer",
            level = 1,
            title = "Explore all six dots",
            description = "Learn every Braille dot position, row, and column.",
            contentJson = LessonContent(
                type = "dot_explorer",
                goal = "User learns dot position, row, and column.",
                dots = listOf(1, 2, 3, 4, 5, 6),
                questions = (1..6).map { dot ->
                    LessonQuestion(
                        id = "dot-$dot-position",
                        prompt = "Find dot $dot on the Braille cell.",
                        correctAnswer = dotPosition(dot),
                        options = listOf("left column", "right column", "top row", "middle row", "bottom row")
                    )
                }
            ).toJson(),
            orderIndex = 1,
            isPremium = false
        )
    }

    private fun letterBuilderLessons(): List<LessonEntity> {
        return gradeOneDots.entries.mapIndexed { index, (letter, dots) ->
            LessonEntity(
                id = "level-2-letter-${letter.lowercase()}",
                level = 2,
                title = "Build letter $letter",
                description = "Learn the Braille dots for letter $letter: ${dots.joinToString(", ")}.",
                contentJson = LessonContent(
                    type = "letter_builder",
                    goal = "Learn which Braille dots form letter $letter.",
                    dots = dots,
                    letter = letter,
                    questions = listOf(
                        LessonQuestion(
                            id = "letter-${letter.lowercase()}-dots",
                            prompt = "Which dots make letter $letter?",
                            correctAnswer = dots.joinToString(","),
                            options = dotOptions(dots)
                        )
                    )
                ).toJson(),
                orderIndex = index + 1,
                isPremium = index >= 5
            )
        }
    }

    private fun recognitionLessons(): List<LessonEntity> {
        return gradeOneDots.entries.chunked(5).mapIndexed { index, group ->
            val letters = group.map { it.key }
            LessonEntity(
                id = "level-3-recognition-${index + 1}",
                level = 3,
                title = "Recognize ${letters.first()}-${letters.last()}",
                description = "Identify random Braille cells from ${letters.joinToString(", ")}.",
                contentJson = LessonContent(
                    type = "letter_recognition",
                    goal = "User identifies the letter from a shown Braille cell.",
                    questions = group.map { (letter, dots) ->
                        LessonQuestion(
                            id = "recognize-${letter.lowercase()}",
                            prompt = "Which letter uses dots ${dots.joinToString(", ")}?",
                            correctAnswer = letter,
                            options = letters
                        )
                    }
                ).toJson(),
                orderIndex = index + 1,
                isPremium = true
            )
        }
    }

    private fun wordReadingLessons(): List<LessonEntity> {
        return simpleWords.mapIndexed { index, word ->
            LessonEntity(
                id = "level-4-word-$word",
                level = 4,
                title = "Read $word",
                description = "Decode the word $word cell by cell.",
                contentJson = LessonContent(
                    type = "word_reading",
                    goal = "User decodes simple three-letter words cell by cell.",
                    word = word,
                    questions = word.mapIndexed { charIndex, char ->
                        val letter = char.uppercase()
                        LessonQuestion(
                            id = "word-$word-$charIndex",
                            prompt = "Letter ${charIndex + 1} uses dots ${gradeOneDots[letter].orEmpty().joinToString(", ")}.",
                            correctAnswer = letter,
                            options = listOf(letter)
                        )
                    }
                ).toJson(),
                orderIndex = index + 1,
                isPremium = true
            )
        }
    }

    private fun contractionLessons(): List<LessonEntity> {
        return Grade2Contractions.initialSet.map { contraction ->
            val options = Grade2Contractions.initialSet
                .map { it.contractionText }
                .filter { it != contraction.contractionText }
                .take(3)
                .plus(contraction.contractionText)
                .sorted()
            LessonEntity(
                id = "level-5-contraction-${contraction.id}",
                level = 5,
                title = "Contraction: ${contraction.contractionText}",
                description = "Learn the Grade 2 contraction for ${contraction.meaning}.",
                contentJson = LessonContent(
                    type = "grade_2_contraction",
                    goal = "Introduce common Grade 2 contractions with an expandable data model.",
                    dots = contraction.dots.sorted(),
                    cells = contraction.cells.map { it.sorted() },
                    contraction = contraction.contractionText,
                    displaySymbol = contraction.displaySymbol,
                    meaning = contraction.meaning,
                    exampleSentence = contraction.exampleSentence,
                    grade = contraction.grade,
                    questions = listOf(
                        LessonQuestion(
                            id = "contraction-${contraction.id}",
                            prompt = "What does this contraction mean?",
                            correctAnswer = contraction.contractionText,
                            options = options
                        )
                    )
                ).toJson(),
                orderIndex = contraction.orderIndex,
                isPremium = true
            )
        }
    }

    private fun scanAndLearnLessons(): List<LessonEntity> {
        return listOf(
            LessonEntity(
                id = "level-6-scan-known-letter",
                level = 6,
                title = "Scan a known letter",
                description = "Use the scanner result to compare a real Braille letter with the lesson answer.",
                contentJson = scanContent("Scan one Braille letter and confirm the detected letter.").toJson(),
                orderIndex = 1,
                isPremium = true
            ),
            LessonEntity(
                id = "level-6-scan-short-word",
                level = 6,
                title = "Scan a short word",
                description = "Practice with a real three-letter Braille word.",
                contentJson = scanContent("Scan a simple word like cat, dog, or sun.").toJson(),
                orderIndex = 2,
                isPremium = true
            ),
            LessonEntity(
                id = "level-6-scan-own-page",
                level = 6,
                title = "Scan your own page",
                description = "Use the existing scanner result as real-world practice.",
                contentJson = scanContent("Scan a real Braille page and review the detected text.").toJson(),
                orderIndex = 3,
                isPremium = true
            )
        )
    }

    private fun scanContent(prompt: String): LessonContent {
        return LessonContent(
            type = "scan_and_learn",
            goal = "Use existing Braille scanner output as real-world learning practice.",
            questions = listOf(
                LessonQuestion(
                    id = "scan-practice",
                    prompt = prompt,
                    correctAnswer = "scanner_result"
                )
            )
        )
    }

    private fun dotPosition(dot: Int): String {
        return when (dot) {
            1 -> "left column, top row"
            2 -> "left column, middle row"
            3 -> "left column, bottom row"
            4 -> "right column, top row"
            5 -> "right column, middle row"
            6 -> "right column, bottom row"
            else -> "unknown"
        }
    }

    private fun dotOptions(correctDots: List<Int>): List<String> {
        val correct = correctDots.joinToString(",")
        return (listOf(correct, "1", "1,2", "1,4", "1,3,5", "2,4,5")
            .distinct()
            .take(4))
    }
}
