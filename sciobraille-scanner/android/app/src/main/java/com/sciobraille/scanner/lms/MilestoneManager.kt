package com.sciobraille.scanner.lms

import android.content.Context

enum class Milestone(val title: String) {
    DOT_EXPLORER_COMPLETE("Dot Explorer Complete"),
    GRADE_1_LETTERS_BEGINNER("Grade 1 Letters Beginner"),
    GRADE_1_LETTERS_COMPLETE("Grade 1 Letters Complete"),
    LETTER_RECOGNITION_70("Letter Recognition 70% Accuracy"),
    WORD_READING_STARTER_COMPLETE("Word Reading Starter Complete"),
    GRADE_2_BEGINNER("Grade 2 Beginner"),
    REAL_WORLD_SCANNER_PRACTICE_COMPLETE("Real World Scanner Practice Complete")
}

data class MilestoneAward(
    val milestone: Milestone,
    val awardedAt: Long
)

/** Evaluates only persisted LMS progress; certificates are local until cloud profile sync exists. */
class MilestoneManager(
    context: Context,
    private val repository: LmsRepository
) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    suspend fun evaluateAndAward(): List<MilestoneAward> {
        val lessons = repository.getLessonsByLanguage(Language.ENGLISH)
        val progress = repository.getAllProgress()
        val completed = progress.filter { it.status == LessonProgressStatus.COMPLETED }
        val completedLevelTwo = completed.count { it.level == 2 }
        val levelThreeAccuracy = completed.filter { it.level == 3 }.map { it.accuracy }.average()
        val levelFourLessons = lessons.count { it.level == 4 }
        val completedLevelFour = completed.filter { it.level == 4 }
        val levelFourAccuracy = completedLevelFour.map { it.accuracy }.average()
        val candidates = buildList {
            if (completed.any { it.lessonId == "level-1-dot-explorer" }) add(Milestone.DOT_EXPLORER_COMPLETE)
            if (completedLevelTwo >= 10) add(Milestone.GRADE_1_LETTERS_BEGINNER)
            if (completedLevelTwo >= 26) add(Milestone.GRADE_1_LETTERS_COMPLETE)
            if (!levelThreeAccuracy.isNaN() && levelThreeAccuracy >= 70.0) add(Milestone.LETTER_RECOGNITION_70)
            if (levelFourLessons > 0 && completedLevelFour.size == levelFourLessons && !levelFourAccuracy.isNaN() && levelFourAccuracy >= 70.0) {
                add(Milestone.WORD_READING_STARTER_COMPLETE)
            }
            if (completed.count { it.level == 5 } >= 3) add(Milestone.GRADE_2_BEGINNER)
            if (completed.any { it.level == 6 }) add(Milestone.REAL_WORLD_SCANNER_PRACTICE_COMPLETE)
        }
        val now = System.currentTimeMillis()
        val newAwards = candidates.filter { preferences.getLong(keyFor(it), 0L) == 0L }
            .map { milestone -> MilestoneAward(milestone, now) }
        if (newAwards.isNotEmpty()) {
            preferences.edit().apply {
                newAwards.forEach { putLong(keyFor(it.milestone), it.awardedAt) }
                apply()
            }
        }
        return newAwards
    }

    fun getAwards(): List<MilestoneAward> = Milestone.entries.mapNotNull { milestone ->
        preferences.getLong(keyFor(milestone), 0L).takeIf { it > 0L }?.let { MilestoneAward(milestone, it) }
    }.sortedByDescending { it.awardedAt }

    fun learnerName(): String = preferences.getString(KEY_LEARNER_NAME, null)?.trim().takeUnless { it.isNullOrBlank() } ?: "Learner"

    private fun keyFor(milestone: Milestone): String = "certificate_${milestone.name}"

    companion object {
        private const val PREFERENCES = "sciobraille_lms_certificates"
        private const val KEY_LEARNER_NAME = "learner_name"
    }
}
