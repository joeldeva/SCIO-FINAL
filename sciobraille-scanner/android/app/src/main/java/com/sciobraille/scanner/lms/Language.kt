package com.sciobraille.scanner.lms

enum class Language(val code: String, val displayName: String) {
    ENGLISH("en", "English"),
    HINDI("hi", "Hindi"),
    TAMIL("ta", "Tamil"),
    KANNADA("kn", "Kannada");

    companion object {
        fun fromCode(code: String?): Language = entries.firstOrNull { it.code == code } ?: ENGLISH
    }
}
