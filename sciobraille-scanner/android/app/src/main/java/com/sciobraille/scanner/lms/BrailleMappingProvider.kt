package com.sciobraille.scanner.lms

/**
 * Single source for language mappings. Only English is populated until verified Indic Braille
 * mappings are reviewed and added to the corresponding language map.
 */
object BrailleMappingProvider {
    private val mappings: Map<Language, Map<Char, Set<Int>>> = mapOf(
        Language.ENGLISH to BrailleMappings.letterToDots,
        Language.HINDI to emptyMap(),
        Language.TAMIL to emptyMap(),
        Language.KANNADA to emptyMap()
    )

    fun getMappings(language: Language): Map<Char, Set<Int>> = mappings[language].orEmpty()

    fun getDotsForCharacter(language: Language, character: Char): Set<Int> =
        getMappings(language)[character.uppercaseChar()].orEmpty()

    fun getCharacterForDots(language: Language, dots: Set<Int>): Char? =
        getMappings(language).entries.firstOrNull { it.value == dots.toSet() }?.key
}
