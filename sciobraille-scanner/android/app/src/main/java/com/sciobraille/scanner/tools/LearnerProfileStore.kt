package com.sciobraille.scanner.tools

import android.content.Context

data class LearnerProfile(
    val name: String = "",
    val age: String = "",
    val learningGoal: String = "Learn Grade 1 Braille",
    val preferredMode: String = "Audio and haptics",
    val languageCode: String = "en"
)

class LearnerProfileStore(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun load(): LearnerProfile = LearnerProfile(
        name = preferences.getString(KEY_NAME, "").orEmpty(),
        age = preferences.getString(KEY_AGE, "").orEmpty(),
        learningGoal = preferences.getString(KEY_GOAL, "Learn Grade 1 Braille").orEmpty(),
        preferredMode = preferences.getString(KEY_MODE, "Audio and haptics").orEmpty(),
        languageCode = preferences.getString(KEY_LANGUAGE, "en").orEmpty()
    )

    fun save(profile: LearnerProfile) {
        preferences.edit()
            .putString(KEY_NAME, profile.name.trim())
            .putString(KEY_AGE, profile.age.trim())
            .putString(KEY_GOAL, profile.learningGoal)
            .putString(KEY_MODE, profile.preferredMode)
            .putString(KEY_LANGUAGE, profile.languageCode)
            .apply()
    }

    companion object {
        private const val PREFERENCES = "sciobraille_learner_profile"
        private const val KEY_NAME = "name"
        private const val KEY_AGE = "age"
        private const val KEY_GOAL = "goal"
        private const val KEY_MODE = "mode"
        private const val KEY_LANGUAGE = "language"
    }
}
