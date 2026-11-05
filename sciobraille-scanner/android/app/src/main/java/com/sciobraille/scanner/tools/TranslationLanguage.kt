package com.sciobraille.scanner.tools

enum class AppLanguage(
    val displayName: String,
    val languageCode: String,
    val localeTag: String,
    val backendCode: String
) {
    ENGLISH("English", "en", "en-IN", "en"),
    TAMIL("Tamil", "ta", "ta-IN", "ta"),
    HINDI("Hindi", "hi", "hi-IN", "hi"),
    TELUGU("Telugu", "te", "te-IN", "te"),
    MALAYALAM("Malayalam", "ml", "ml-IN", "ml"),
    KANNADA("Kannada", "kn", "kn-IN", "kn"),
    BENGALI("Bengali", "bn", "bn", "bn"),
    MARATHI("Marathi", "mr", "mr", "mr"),
    GUJARATI("Gujarati", "gu", "gu", "gu"),
    PUNJABI("Punjabi", "pa", "pa", "pa"),
    URDU("Urdu", "ur", "ur", "ur"),
    ODIA_ORIYA("Odia (Oriya)", "or", "or", "or"),
    ASSAMESE("Assamese", "as", "as", "as"),
    SANSKRIT("Sanskrit", "sa", "sa", "sa"),
    AFRIKAANS("Afrikaans", "af", "af", "af"),
    ALBANIAN("Albanian", "sq", "sq", "sq"),
    AMHARIC("Amharic", "am", "am", "am"),
    ARABIC("Arabic", "ar", "ar", "ar"),
    ARMENIAN("Armenian", "hy", "hy", "hy"),
    AYMARA("Aymara", "ay", "ay", "ay"),
    AZERBAIJANI("Azerbaijani", "az", "az", "az"),
    BAMBARA("Bambara", "bm", "bm", "bm"),
    BASQUE("Basque", "eu", "eu", "eu"),
    BELARUSIAN("Belarusian", "be", "be", "be"),
    BHOJPURI("Bhojpuri", "bho", "bho", "bho"),
    BOSNIAN("Bosnian", "bs", "bs", "bs"),
    BULGARIAN("Bulgarian", "bg", "bg", "bg"),
    CATALAN("Catalan", "ca", "ca", "ca"),
    CEBUANO("Cebuano", "ceb", "ceb", "ceb"),
    CHICHEWA("Chichewa", "ny", "ny", "ny"),
    CHINESE("Chinese (Simplified)", "zh-CN", "zh-CN", "zh-CN"),
    CHINESE_TRADITIONAL("Chinese (Traditional)", "zh-TW", "zh-TW", "zh-TW"),
    CORSICAN("Corsican", "co", "co", "co"),
    CROATIAN("Croatian", "hr", "hr", "hr"),
    CZECH("Czech", "cs", "cs", "cs"),
    DANISH("Danish", "da", "da", "da"),
    DHIVEHI("Dhivehi", "dv", "dv", "dv"),
    DOGRI("Dogri", "doi", "doi", "doi"),
    DUTCH("Dutch", "nl", "nl", "nl"),
    ESPERANTO("Esperanto", "eo", "eo", "eo"),
    ESTONIAN("Estonian", "et", "et", "et"),
    EWE("Ewe", "ee", "ee", "ee"),
    FILIPINO("Filipino", "tl", "tl", "tl"),
    FINNISH("Finnish", "fi", "fi", "fi"),
    FRENCH("French", "fr", "fr", "fr"),
    FRISIAN("Frisian", "fy", "fy", "fy"),
    GALICIAN("Galician", "gl", "gl", "gl"),
    GEORGIAN("Georgian", "ka", "ka", "ka"),
    GERMAN("German", "de", "de", "de"),
    GREEK("Greek", "el", "el", "el"),
    GUARANI("Guarani", "gn", "gn", "gn"),
    HAITIAN_CREOLE("Haitian Creole", "ht", "ht", "ht"),
    HAUSA("Hausa", "ha", "ha", "ha"),
    HAWAIIAN("Hawaiian", "haw", "haw", "haw"),
    HEBREW("Hebrew", "iw", "he", "iw"),
    HMONG("Hmong", "hmn", "hmn", "hmn"),
    HUNGARIAN("Hungarian", "hu", "hu", "hu"),
    ICELANDIC("Icelandic", "is", "is", "is"),
    IGBO("Igbo", "ig", "ig", "ig"),
    ILOCANO("Ilocano", "ilo", "ilo", "ilo"),
    INDONESIAN("Indonesian", "id", "id", "id"),
    IRISH("Irish", "ga", "ga", "ga"),
    ITALIAN("Italian", "it", "it", "it"),
    JAPANESE("Japanese", "ja", "ja", "ja"),
    JAVANESE("Javanese", "jw", "jv", "jw"),
    KAZAKH("Kazakh", "kk", "kk", "kk"),
    KHMER("Khmer", "km", "km", "km"),
    KINYARWANDA("Kinyarwanda", "rw", "rw", "rw"),
    KONKANI("Konkani", "gom", "gom", "gom"),
    KOREAN("Korean", "ko", "ko", "ko"),
    KRIO("Krio", "kri", "kri", "kri"),
    KURDISH_KURMANJI("Kurdish (Kurmanji)", "ku", "ku", "ku"),
    KURDISH_SORANI("Kurdish (Sorani)", "ckb", "ckb", "ckb"),
    KYRGYZ("Kyrgyz", "ky", "ky", "ky"),
    LAO("Lao", "lo", "lo", "lo"),
    LATIN("Latin", "la", "la", "la"),
    LATVIAN("Latvian", "lv", "lv", "lv"),
    LINGALA("Lingala", "ln", "ln", "ln"),
    LITHUANIAN("Lithuanian", "lt", "lt", "lt"),
    LUGANDA("Luganda", "lg", "lg", "lg"),
    LUXEMBOURGISH("Luxembourgish", "lb", "lb", "lb"),
    MACEDONIAN("Macedonian", "mk", "mk", "mk"),
    MAITHILI("Maithili", "mai", "mai", "mai"),
    MALAGASY("Malagasy", "mg", "mg", "mg"),
    MALAY("Malay", "ms", "ms", "ms"),
    MALTESE("Maltese", "mt", "mt", "mt"),
    MAORI("Maori", "mi", "mi", "mi"),
    MEITEILON_MANIPURI("Meiteilon (Manipuri)", "mni-Mtei", "mni-Mtei", "mni-Mtei"),
    MIZO("Mizo", "lus", "lus", "lus"),
    MONGOLIAN("Mongolian", "mn", "mn", "mn"),
    MYANMAR("Myanmar", "my", "my", "my"),
    NEPALI("Nepali", "ne", "ne", "ne"),
    NORWEGIAN("Norwegian", "no", "no", "no"),
    OROMO("Oromo", "om", "om", "om"),
    PASHTO("Pashto", "ps", "ps", "ps"),
    PERSIAN("Persian", "fa", "fa", "fa"),
    POLISH("Polish", "pl", "pl", "pl"),
    PORTUGUESE("Portuguese", "pt", "pt", "pt"),
    QUECHUA("Quechua", "qu", "qu", "qu"),
    ROMANIAN("Romanian", "ro", "ro", "ro"),
    RUSSIAN("Russian", "ru", "ru", "ru"),
    SAMOAN("Samoan", "sm", "sm", "sm"),
    SCOTS_GAELIC("Scots Gaelic", "gd", "gd", "gd"),
    SEPEDI("Sepedi", "nso", "nso", "nso"),
    SERBIAN("Serbian", "sr", "sr", "sr"),
    SESOTHO("Sesotho", "st", "st", "st"),
    SHONA("Shona", "sn", "sn", "sn"),
    SINDHI("Sindhi", "sd", "sd", "sd"),
    SINHALA("Sinhala", "si", "si", "si"),
    SLOVAK("Slovak", "sk", "sk", "sk"),
    SLOVENIAN("Slovenian", "sl", "sl", "sl"),
    SOMALI("Somali", "so", "so", "so"),
    SPANISH("Spanish", "es", "es", "es"),
    SUNDANESE("Sundanese", "su", "su", "su"),
    SWAHILI("Swahili", "sw", "sw", "sw"),
    SWEDISH("Swedish", "sv", "sv", "sv"),
    TAJIK("Tajik", "tg", "tg", "tg"),
    TATAR("Tatar", "tt", "tt", "tt"),
    THAI("Thai", "th", "th", "th"),
    TIGRINYA("Tigrinya", "ti", "ti", "ti"),
    TSONGA("Tsonga", "ts", "ts", "ts"),
    TURKISH("Turkish", "tr", "tr", "tr"),
    TURKMEN("Turkmen", "tk", "tk", "tk"),
    TWI("Twi", "ak", "ak", "ak"),
    UKRAINIAN("Ukrainian", "uk", "uk", "uk"),
    UYGHUR("Uyghur", "ug", "ug", "ug"),
    UZBEK("Uzbek", "uz", "uz", "uz"),
    VIETNAMESE("Vietnamese", "vi", "vi", "vi"),
    WELSH("Welsh", "cy", "cy", "cy"),
    XHOSA("Xhosa", "xh", "xh", "xh"),
    YIDDISH("Yiddish", "yi", "yi", "yi"),
    YORUBA("Yoruba", "yo", "yo", "yo"),
    ZULU("Zulu", "zu", "zu", "zu");

    val nativeName: String get() = java.util.Locale.forLanguageTag(localeTag).getDisplayLanguage(java.util.Locale.forLanguageTag(localeTag))
    val offlineCode: String? get() = when (languageCode) {
        "zh-TW" -> null // Do not substitute Simplified Chinese for Traditional Chinese.
        "zh-CN" -> "zh"
        "iw" -> "he"
        "jw" -> "jv"
        else -> languageCode
    }
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
