package com.sciobraille.scanner.lms

enum class MasteryBand { NEW, LEARNING, IMPROVING, MASTERED }

data class LetterAttempt(
    val letter: Char,
    val correct: Boolean,
    val timestamp: Long
)

data class LetterMastery(
    val letter: Char,
    val attempts: Int,
    val correct: Int,
    val incorrect: Int,
    val accuracy: Float,
    val recentAccuracy: Float,
    val lastPracticed: Long?,
    val recentlyIncorrect: Boolean,
    val masteryBand: MasteryBand,
    val recommendationReason: String
)

object LetterMasteryRules {
    const val MASTERED_ACCURACY = 85f
    const val IMPROVING_ACCURACY = 60f
    const val MIN_MASTERED_ATTEMPTS = 5
    const val RECENT_WINDOW = 5
    const val STALE_DAYS = 14

    fun calculate(attempts: List<LetterAttempt>, now: Long = System.currentTimeMillis()): List<LetterMastery> {
        val grouped = attempts.groupBy { it.letter.uppercaseChar() }
        return ('A'..'Z').map { letter ->
            val values = grouped[letter].orEmpty().sortedByDescending { it.timestamp }
            val recent = values.take(RECENT_WINDOW)
            val accuracy = percentage(values)
            val recentAccuracy = percentage(recent)
            val band = when {
                values.isEmpty() -> MasteryBand.NEW
                values.size >= MIN_MASTERED_ATTEMPTS && recentAccuracy >= MASTERED_ACCURACY -> MasteryBand.MASTERED
                recentAccuracy >= IMPROVING_ACCURACY -> MasteryBand.IMPROVING
                else -> MasteryBand.LEARNING
            }
            val last = values.firstOrNull()?.timestamp
            val stale = last == null || now - last >= STALE_DAYS * 86_400_000L
            val reason = when {
                values.isEmpty() -> "$letter is recommended because it has not been practiced yet."
                recent.any { !it.correct } && recentAccuracy < IMPROVING_ACCURACY ->
                    "$letter is recommended because recent accuracy is ${recentAccuracy.toInt()}%."
                stale -> "$letter is recommended because it has not been practiced recently."
                else -> "$letter is recommended to reinforce ${recentAccuracy.toInt()}% recent accuracy."
            }
            LetterMastery(
                letter = letter,
                attempts = values.size,
                correct = values.count { it.correct },
                incorrect = values.count { !it.correct },
                accuracy = accuracy,
                recentAccuracy = recentAccuracy,
                lastPracticed = last,
                recentlyIncorrect = recent.firstOrNull()?.correct == false,
                masteryBand = band,
                recommendationReason = reason
            )
        }
    }

    fun prioritize(
        mastery: List<LetterMastery>,
        unfinishedLetters: Set<Char>,
        limit: Int = 3
    ): List<LetterMastery> = mastery.sortedWith(
        compareBy<LetterMastery> { if (it.masteryBand == MasteryBand.MASTERED) 1 else 0 }
            .thenBy { it.recentAccuracy }
            .thenByDescending { it.letter in unfinishedLetters }
            .thenByDescending { it.recentlyIncorrect }
            .thenBy { it.lastPracticed ?: Long.MIN_VALUE }
            .thenBy { it.letter }
    ).take(limit)

    private fun percentage(values: List<LetterAttempt>): Float =
        if (values.isEmpty()) 0f else values.count { it.correct } * 100f / values.size
}
