package com.sciobraille.scanner

import android.content.res.Configuration

internal object ScioColors {
    var dark = false
    var contrast = false
    fun configure(preferences: AccessibilityPreferences, configuration: Configuration) {
        dark = when (preferences.theme) {
            ThemePreference.DARK -> true
            ThemePreference.LIGHT -> false
            ThemePreference.SYSTEM -> configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
        }
        contrast = preferences.highContrast
    }
    val BACKGROUND get() = if (dark) 0xFF10141B.toInt() else 0xFFF7F8FC.toInt()
    val SURFACE get() = if (dark) 0xFF1A202B.toInt() else 0xFFFFFFFF.toInt()
    val SURFACE_CONTAINER get() = if (dark) 0xFF252E3C.toInt() else 0xFFECEFF7.toInt()
    val SURFACE_HIGH get() = SURFACE_CONTAINER
    val TEXT get() = if (dark) 0xFFF8FAFF.toInt() else 0xFF172039.toInt()
    val MUTED get() = if (contrast) TEXT else if (dark) 0xFFC3CBDC.toInt() else 0xFF4B5870.toInt()
    val OUTLINE get() = if (contrast) TEXT else if (dark) 0xFF63718A.toInt() else 0xFFABB5CC.toInt()
    val PRIMARY get() = if (dark) 0xFFCCC4FF.toInt() else 0xFF4C3BA8.toInt()
    val PRIMARY_CONTAINER get() = 0xFF4C3BA8.toInt()
    val PRIMARY_FIXED get() = if (dark) 0xFF2D2851.toInt() else 0xFFEAE5FF.toInt()
    val SECONDARY get() = if (dark) 0xFF9CE6D8.toInt() else 0xFF075B51.toInt()
    val SECONDARY_CONTAINER get() = if (dark) 0xFF172D30.toInt() else 0xFFE5F6F1.toInt()
    val SECONDARY_FIXED get() = SECONDARY_CONTAINER
    val DARK get() = 0xFF10141B.toInt()
    val ERROR get() = if (dark) 0xFFFFB4AB.toInt() else 0xFFB01F30.toInt()
}
