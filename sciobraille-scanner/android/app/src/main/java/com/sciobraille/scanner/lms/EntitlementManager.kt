package com.sciobraille.scanner.lms

import android.content.Context

enum class AccountType {
    FREE,
    PREMIUM_INDIVIDUAL,
    SCHOOL_STUDENT,
    TEACHER,
    ADMIN
}

/** Local entitlement boundary until billing and school-code verification are connected. */
class EntitlementManager(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun accountType(): AccountType = runCatching {
        AccountType.valueOf(preferences.getString(KEY_ACCOUNT_TYPE, AccountType.FREE.name).orEmpty())
    }.getOrDefault(AccountType.FREE)

    fun hasFullLearningAccess(): Boolean = accountType() != AccountType.FREE

    fun canAccessLetter(letter: Char): Boolean = hasFullLearningAccess() || letter.uppercaseChar() in 'A'..'E'

    fun canAccessLevel(level: Int): Boolean = when (level) {
        1, 2 -> true
        3 -> hasFullLearningAccess() || freeRecognitionSessionsRemaining() > 0
        else -> hasFullLearningAccess()
    }

    fun canUseCloudSync(): Boolean = hasFullLearningAccess()

    fun canAccessTeacherDashboard(): Boolean = accountType() == AccountType.TEACHER || accountType() == AccountType.ADMIN

    fun canAccessReports(): Boolean = canAccessTeacherDashboard() || accountType() == AccountType.SCHOOL_STUDENT

    fun freeRecognitionSessionsRemaining(): Int = (FREE_RECOGNITION_SESSIONS - preferences
        .getInt(KEY_FREE_RECOGNITION_SESSIONS_USED, 0)).coerceAtLeast(0)

    fun consumeFreeRecognitionSession(): Boolean {
        if (hasFullLearningAccess()) return true
        if (freeRecognitionSessionsRemaining() == 0) return false
        preferences.edit()
            .putInt(KEY_FREE_RECOGNITION_SESSIONS_USED, preferences.getInt(KEY_FREE_RECOGNITION_SESSIONS_USED, 0) + 1)
            .apply()
        return true
    }

    fun savePendingSchoolCode(code: String) {
        preferences.edit().putString(KEY_PENDING_SCHOOL_CODE, code.trim()).apply()
    }

    fun lockedReason(feature: String): String = "$feature is available with Premium."

    companion object {
        private const val PREFERENCES = "sciobraille_lms_entitlements"
        private const val KEY_ACCOUNT_TYPE = "account_type"
        private const val KEY_FREE_RECOGNITION_SESSIONS_USED = "free_recognition_sessions_used"
        private const val KEY_PENDING_SCHOOL_CODE = "pending_school_code"
        private const val FREE_RECOGNITION_SESSIONS = 1
    }
}
