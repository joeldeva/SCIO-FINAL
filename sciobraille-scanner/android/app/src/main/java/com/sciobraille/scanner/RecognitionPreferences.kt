package com.sciobraille.scanner

import android.content.Context

enum class ScanSideMode(val displayName: String, val description: String) {
    AUTOMATIC(
        "Automatic (both sides)",
        "Checks front-side and reverse-side Braille, then keeps the stronger reading."
    ),
    FRONT_ONLY(
        "Front side only",
        "Reads raised dots exactly as photographed without horizontal mirroring."
    ),
    REVERSE_ONLY(
        "Reverse side only",
        "Horizontally mirrors the image before recognition for Braille photographed from the back."
    );

    companion object {
        fun fromStored(value: String?): ScanSideMode =
            entries.firstOrNull { it.name == value } ?: AUTOMATIC
    }
}

data class RecognitionPreferences(
    val sideMode: ScanSideMode = ScanSideMode.AUTOMATIC,
    val showAnnotatedResult: Boolean = true
)

class RecognitionPreferencesStore(context: Context) {
    private val preferences = context.getSharedPreferences("recognition_preferences", Context.MODE_PRIVATE)

    fun load(): RecognitionPreferences = RecognitionPreferences(
        sideMode = ScanSideMode.fromStored(preferences.getString(KEY_SIDE_MODE, null)),
        showAnnotatedResult = preferences.getBoolean(KEY_SHOW_ANNOTATED_RESULT, true)
    )

    fun save(value: RecognitionPreferences) {
        preferences.edit()
            .putString(KEY_SIDE_MODE, value.sideMode.name)
            .putBoolean(KEY_SHOW_ANNOTATED_RESULT, value.showAnnotatedResult)
            .apply()
    }

    private companion object {
        const val KEY_SIDE_MODE = "side_mode"
        const val KEY_SHOW_ANNOTATED_RESULT = "show_annotated_result"
    }
}

internal object OfflineOrientationPolicy {
    fun candidates(mode: ScanSideMode): List<Boolean> = when (mode) {
        ScanSideMode.AUTOMATIC -> listOf(true, false)
        ScanSideMode.FRONT_ONLY -> listOf(false)
        ScanSideMode.REVERSE_ONLY -> listOf(true)
    }
}
