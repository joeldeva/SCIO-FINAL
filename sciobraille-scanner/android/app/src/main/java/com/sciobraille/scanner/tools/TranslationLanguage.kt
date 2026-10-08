package com.sciobraille.scanner.tools

enum class AppLanguage(
    val displayName: String,
    val languageCode: String,
    val localeTag: String,
    val backendCode: String
) {
    ENGLISH("English", "en", "en-IN", "en"),
    HINDI("Hindi", "hi", "hi-IN", "hi"),
    TAMIL("Tamil", "ta", "ta-IN", "ta"),
    TELUGU("Telugu", "te", "te-IN", "te"),
    MALAYALAM("Malayalam", "ml", "ml-IN", "ml"),
    KANNADA("Kannada", "kn", "kn-IN", "kn"),
    SPANISH("Spanish", "es", "es-ES", "es"),
    FRENCH("French", "fr", "fr-FR", "fr"),
    GERMAN("German", "de", "de-DE", "de"),
    CHINESE("Chinese", "zh-CN", "zh-CN", "zh-CN"),
    JAPANESE("Japanese", "ja", "ja-JP", "ja");

    // Compatibility aliases for older Story Reader code.
    val code: String get() = backendCode
    val ttsTag: String get() = localeTag

    companion object {
        fun fromCode(code: String?): AppLanguage = entries.firstOrNull {
            it.languageCode.equals(code, true) ||
                it.backendCode.equals(code, true) ||
                it.localeTag.equals(code, true)
        } ?: ENGLISH

        fun fromCommand(command: String): AppLanguage? = entries.firstOrNull {
            command.contains(it.displayName, ignoreCase = true)
        }
    }
}

typealias TranslationLanguage = AppLanguage

object TranslationLanguages {
    val supported: List<AppLanguage> = AppLanguage.entries
}
