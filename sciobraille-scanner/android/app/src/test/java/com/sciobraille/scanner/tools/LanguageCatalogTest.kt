package com.sciobraille.scanner.tools
import org.junit.Assert.*
import org.junit.Test
class LanguageCatalogTest {
 @Test fun codesAreUniqueAndPriorityLanguagesExist() { val codes=AppLanguage.entries.map { it.backendCode }; assertEquals(codes.size,codes.toSet().size);assertTrue(codes.containsAll(listOf("ta","hi","te","ml","kn","bn","mr","gu","pa","ur","or","as","sa"))) }
 @Test fun traditionalChineseIsNeverSubstitutedBySimplifiedOffline() { assertNull(AppLanguage.CHINESE_TRADITIONAL.offlineCode);assertEquals("zh",AppLanguage.CHINESE.offlineCode) }
 @Test fun languagePreferenceRoundTrips() { AppLanguage.entries.forEach { assertEquals(it,AppLanguage.fromCode(it.languageCode)) } }
}
