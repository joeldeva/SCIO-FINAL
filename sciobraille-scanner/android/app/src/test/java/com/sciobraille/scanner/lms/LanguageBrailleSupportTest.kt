package com.sciobraille.scanner.lms

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LanguageBrailleSupportTest {
    @Test
    fun englishMappingsRemainAvailableThroughLanguageProvider() {
        assertEquals(setOf(1, 2), BrailleMappingProvider.getDotsForCharacter(Language.ENGLISH, 'B'))
        assertEquals('B', BrailleMappingProvider.getCharacterForDots(Language.ENGLISH, setOf(1, 2)))
    }

    @Test
    fun unverifiedIndianLanguageMappingsStayEmpty() {
        listOf(Language.HINDI, Language.TAMIL, Language.KANNADA).forEach { language ->
            assertTrue(BrailleMappingProvider.getMappings(language).isEmpty())
            assertTrue(BrailleMappingProvider.getDotsForCharacter(language, 'A').isEmpty())
            assertNull(BrailleMappingProvider.getCharacterForDots(language, setOf(1)))
        }
    }

    @Test
    fun curriculumHasComingSoonEntriesForUnverifiedLanguages() {
        val lessons = LmsCurriculumProvider.defaultLessons()
        listOf(Language.HINDI, Language.TAMIL, Language.KANNADA).forEach { language ->
            assertTrue(lessons.any {
                it.languageCode == language.code && it.description == "This language curriculum is coming soon."
            })
        }
    }
}
