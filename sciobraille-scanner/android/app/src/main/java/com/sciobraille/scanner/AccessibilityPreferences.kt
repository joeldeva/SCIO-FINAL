package com.sciobraille.scanner

import android.content.Context

enum class ScannerPreference { AUTO, ONLINE_PREFERRED, OFFLINE_PREFERRED }
enum class LearningModePreference { AUDIO, VISUAL, HAPTIC, MIXED }
enum class TextSizePreference(val scale: Float) { STANDARD(1f), LARGE(1.18f), EXTRA_LARGE(1.35f) }

data class AccessibilityPreferences(
    val speechRate: Float = 0.92f,
    val speechPitch: Float = 1f,
    val autoSpeakScan: Boolean = false,
    val speechLanguageTag: String = "en-US",
    val hapticsEnabled: Boolean = true,
    val lessonHaptics: Boolean = true,
    val successErrorHaptics: Boolean = true,
    val hapticIntensity: Int = 2,
    val textSize: TextSizePreference = TextSizePreference.STANDARD,
    val highContrast: Boolean = false,
    val reducedMotion: Boolean = false,
    val showConfidenceIndicators: Boolean = true,
    val scannerMode: ScannerPreference = ScannerPreference.AUTO,
    val autoOrientation: Boolean = true,
    val showDetectionBoxes: Boolean = true,
    val showConfidence: Boolean = true,
    val smartGuidance: Boolean = true,
    val preferredTranslationLanguage: String = "en",
    val autoOpenTranslation: Boolean = false,
    val autoSpeakTranslation: Boolean = false,
    val learningMode: LearningModePreference = LearningModePreference.MIXED
)

class AccessibilityPreferencesStore(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)

    fun load(): AccessibilityPreferences = AccessibilityPreferences(
        speechRate = preferences.getFloat("speechRate", 0.92f).coerceIn(0.5f, 1.5f),
        speechPitch = preferences.getFloat("speechPitch", 1f).coerceIn(0.5f, 1.5f),
        autoSpeakScan = preferences.getBoolean("autoSpeakScan", false),
        speechLanguageTag = preferences.getString("speechLanguageTag", "en-US").orEmpty().ifBlank { "en-US" },
        hapticsEnabled = preferences.getBoolean("hapticsEnabled", true),
        lessonHaptics = preferences.getBoolean("lessonHaptics", true),
        successErrorHaptics = preferences.getBoolean("successErrorHaptics", true),
        hapticIntensity = preferences.getInt("hapticIntensity", 2).coerceIn(1, 3),
        textSize = enumValue(preferences.getString("textSize", null), TextSizePreference.STANDARD),
        highContrast = preferences.getBoolean("highContrast", false),
        reducedMotion = preferences.getBoolean("reducedMotion", false),
        showConfidenceIndicators = preferences.getBoolean("showConfidenceIndicators", true),
        scannerMode = enumValue(preferences.getString("scannerMode", null), ScannerPreference.AUTO),
        autoOrientation = preferences.getBoolean("autoOrientation", true),
        showDetectionBoxes = preferences.getBoolean("showDetectionBoxes", true),
        showConfidence = preferences.getBoolean("showConfidence", true),
        smartGuidance = preferences.getBoolean("smartGuidance", true),
        preferredTranslationLanguage = preferences.getString("preferredTranslationLanguage", "en").orEmpty().ifBlank { "en" },
        autoOpenTranslation = preferences.getBoolean("autoOpenTranslation", false),
        autoSpeakTranslation = preferences.getBoolean("autoSpeakTranslation", false),
        learningMode = enumValue(preferences.getString("learningMode", null), LearningModePreference.MIXED)
    )

    fun save(value: AccessibilityPreferences) {
        preferences.edit()
            .putFloat("speechRate", value.speechRate)
            .putFloat("speechPitch", value.speechPitch)
            .putBoolean("autoSpeakScan", value.autoSpeakScan)
            .putString("speechLanguageTag", value.speechLanguageTag)
            .putBoolean("hapticsEnabled", value.hapticsEnabled)
            .putBoolean("lessonHaptics", value.lessonHaptics)
            .putBoolean("successErrorHaptics", value.successErrorHaptics)
            .putInt("hapticIntensity", value.hapticIntensity)
            .putString("textSize", value.textSize.name)
            .putBoolean("highContrast", value.highContrast)
            .putBoolean("reducedMotion", value.reducedMotion)
            .putBoolean("showConfidenceIndicators", value.showConfidenceIndicators)
            .putString("scannerMode", value.scannerMode.name)
            .putBoolean("autoOrientation", value.autoOrientation)
            .putBoolean("showDetectionBoxes", value.showDetectionBoxes)
            .putBoolean("showConfidence", value.showConfidence)
            .putBoolean("smartGuidance", value.smartGuidance)
            .putString("preferredTranslationLanguage", value.preferredTranslationLanguage)
            .putBoolean("autoOpenTranslation", value.autoOpenTranslation)
            .putBoolean("autoSpeakTranslation", value.autoSpeakTranslation)
            .putString("learningMode", value.learningMode.name)
            .apply()
    }

    private inline fun <reified T : Enum<T>> enumValue(raw: String?, fallback: T): T =
        enumValues<T>().firstOrNull { it.name == raw } ?: fallback

    private companion object { const val NAME = "sciobraille_accessibility_preferences" }
}
