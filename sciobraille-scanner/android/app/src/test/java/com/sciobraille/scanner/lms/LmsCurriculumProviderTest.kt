package com.sciobraille.scanner.lms

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LmsCurriculumProviderTest {
    @Test
    fun defaultCurriculumContainsExpectedLevelsAndLetters() {
        val lessons = LmsCurriculumProvider.defaultLessons()

        assertTrue(lessons.any { it.level == 1 && it.title == "Explore all six dots" })
        assertEquals(26, lessons.count { it.level == 2 })
        assertTrue(lessons.any { it.level == 4 && it.title == "Read cat" })
        assertEquals(11, lessons.count { it.level == 5 })
        assertTrue(lessons.any { it.level == 5 && it.title == "Contraction: the" })
        assertTrue(lessons.any { it.level == 6 && it.id == "level-6-scan-own-page" })
    }

    @Test
    fun lessonContentRoundTripsFromJson() {
        val letterA = LmsCurriculumProvider.defaultLessons()
            .first { it.id == "level-2-letter-a" }

        val content = LessonContent.fromJson(letterA.contentJson)

        assertEquals("letter_builder", content.type)
        assertEquals("A", content.letter)
        assertEquals(listOf(1), content.dots)
        assertEquals("1", content.questions.first().correctAnswer)
    }

    @Test
    fun gradeTwoContractionContentIncludesExpandableMetadata() {
        val the = LmsCurriculumProvider.defaultLessons()
            .first { it.id == "level-5-contraction-the" }

        val content = LessonContent.fromJson(the.contentJson)

        assertEquals("grade_2_contraction", content.type)
        assertEquals("the", content.contraction)
        assertEquals(listOf(listOf(2, 3, 4, 6)), content.cells)
        assertEquals("the word the", content.meaning)
        assertEquals(2, content.grade)
        assertEquals("the", content.questions.first().correctAnswer)
    }
}
