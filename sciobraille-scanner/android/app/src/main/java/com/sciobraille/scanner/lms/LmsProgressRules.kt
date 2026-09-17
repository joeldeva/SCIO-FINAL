package com.sciobraille.scanner.lms

object LmsProgressRules {
    fun completionPercent(completed: Int, total: Int): Int =
        if (total <= 0) 0 else ((completed.coerceIn(0, total) * 100f) / total).toInt()

    fun averageCompletedAccuracy(progress: List<LessonProgressEntity>, level: Int): Float {
        val completed = progress.filter { it.level == level && it.status == LessonProgressStatus.COMPLETED }
        return completed.map { it.accuracy }.average().takeIf { !it.isNaN() }?.toFloat() ?: 0f
    }

    fun isLevelComplete(completed: Int, total: Int, requiredAccuracy: Float? = null, actualAccuracy: Float = 0f): Boolean =
        total > 0 && completed == total && (requiredAccuracy == null || actualAccuracy >= requiredAccuracy)

    fun canUnlockLetterBuilder(levelOneComplete: Boolean): Boolean = levelOneComplete

    fun canUnlockRecognition(isPremium: Boolean, completedLetters: Int, freeSessionAvailable: Boolean): Boolean =
        if (isPremium) completedLetters >= 10 else completedLetters >= 5 && freeSessionAvailable

    fun canUnlockPremiumLevel(isPremium: Boolean, prerequisiteMet: Boolean): Boolean = isPremium && prerequisiteMet
}
