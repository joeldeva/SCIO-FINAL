package com.sciobraille.scanner.lms

import android.content.Context
import java.time.LocalDate
import java.util.UUID
import kotlin.math.max

class LmsRepository private constructor(
    private val lessonDao: LessonDao,
    private val lessonProgressDao: LessonProgressDao,
    private val userScoreDao: UserScoreDao,
    private val streakDao: StreakDao
) {
    suspend fun getLessonsByLevel(level: Int): List<LessonEntity> {
        return lessonDao.getLessonsByLevel(level)
    }

    suspend fun getAllLessons(): List<LessonEntity> {
        return lessonDao.getAllLessons()
    }

    suspend fun getLessonsByLanguage(language: Language): List<LessonEntity> =
        lessonDao.getLessonsByLanguage(language.code)

    suspend fun seedDefaultCurriculumIfNeeded(): Int {
        val existing = lessonDao.getAllLessons().map { it.id }.toSet()
        val missingLessons = LmsCurriculumProvider.defaultLessons().filterNot { it.id in existing }
        if (missingLessons.isNotEmpty()) lessonDao.insertLessons(missingLessons)
        return lessonDao.countLessons()
    }

    suspend fun getProgressForLesson(lessonId: String): LessonProgressEntity? {
        return lessonProgressDao.getProgressForLesson(lessonId)
    }

    suspend fun getAllProgress(): List<LessonProgressEntity> {
        return lessonProgressDao.getAllProgress()
    }

    suspend fun getProgressPendingSync(): List<LessonProgressEntity> = lessonProgressDao.getPendingSync()

    suspend fun getScoresPendingSync(): List<UserScoreEntity> = userScoreDao.getPendingSync()

    suspend fun getStreakPendingSync(): StreakEntity? = streakDao.getStreak()

    suspend fun updateProgressSyncStatus(id: String, status: SyncStatus, lastSyncedAt: Long?) {
        lessonProgressDao.updateSyncStatus(id, status.name, lastSyncedAt)
    }

    suspend fun updateScoreSyncStatus(id: String, status: SyncStatus, lastSyncedAt: Long?) {
        userScoreDao.updateSyncStatus(id, status.name, lastSyncedAt)
    }

    suspend fun updateStreakSyncStatus(id: String, status: SyncStatus, lastSyncedAt: Long?) {
        streakDao.updateSyncStatus(id, status.name, lastSyncedAt)
    }

    suspend fun markLessonStarted(lessonId: String, level: Int): LessonProgressEntity {
        val now = System.currentTimeMillis()
        val existing = lessonProgressDao.getProgressForLesson(lessonId)
        val next = existing?.copy(
            status = if (existing.status == LessonProgressStatus.COMPLETED) {
                LessonProgressStatus.COMPLETED
            } else {
                LessonProgressStatus.IN_PROGRESS
            },
            updatedAt = now,
            syncStatus = SyncStatus.NOT_SYNCED.name,
            lastSyncedAt = null
        ) ?: LessonProgressEntity(
            id = lessonId,
            lessonId = lessonId,
            level = level,
            status = LessonProgressStatus.IN_PROGRESS,
            score = 0,
            accuracy = 0f,
            attempts = 0,
            completedAt = null,
            updatedAt = now,
            syncStatus = SyncStatus.NOT_SYNCED.name,
            lastSyncedAt = null
        )
        lessonProgressDao.upsertProgress(next)
        updateStreak()
        return next
    }

    suspend fun markLessonCompleted(
        lessonId: String,
        level: Int,
        score: Int,
        accuracy: Float
    ): LessonProgressEntity {
        val now = System.currentTimeMillis()
        val existing = lessonProgressDao.getProgressForLesson(lessonId)
        val next = LessonProgressEntity(
            id = existing?.id ?: lessonId,
            lessonId = lessonId,
            level = level,
            status = LessonProgressStatus.COMPLETED,
            score = score.coerceAtLeast(0),
            accuracy = accuracy.coerceIn(0f, 100f),
            attempts = (existing?.attempts ?: 0) + 1,
            completedAt = now,
            updatedAt = now,
            syncStatus = SyncStatus.NOT_SYNCED.name,
            lastSyncedAt = null
        )
        lessonProgressDao.upsertProgress(next)
        updateStreak()
        return next
    }

    suspend fun saveUserScore(
        lessonId: String,
        questionId: String,
        userAnswer: String,
        correctAnswer: String,
        isCorrect: Boolean,
        timestamp: Long = System.currentTimeMillis(),
        id: String = UUID.randomUUID().toString()
    ): UserScoreEntity {
        val score = UserScoreEntity(
            id = id,
            lessonId = lessonId,
            questionId = questionId,
            userAnswer = userAnswer,
            correctAnswer = correctAnswer,
            isCorrect = isCorrect,
            timestamp = timestamp
        )
        userScoreDao.insertScore(score)
        updateStreak()
        return score
    }

    suspend fun getScoresForLetter(letter: Char): List<UserScoreEntity> {
        return userScoreDao.getScoresForCorrectAnswer(letter.uppercaseChar().toString())
    }

    suspend fun getAccuracyForLetter(letter: Char): Float {
        val scores = getScoresForLetter(letter)
        if (scores.isEmpty()) return 0f
        return (scores.count { it.isCorrect } * 100f) / scores.size
    }

    suspend fun getAllLetterAccuracies(): Map<Char, Float> {
        return userScoreDao.getAllScores()
            .filter { it.correctAnswer.length == 1 && it.correctAnswer.first().isLetter() }
            .groupBy { it.correctAnswer.uppercase().first() }
            .mapValues { (_, scores) ->
                if (scores.isEmpty()) 0f else (scores.count { it.isCorrect } * 100f) / scores.size
            }
    }

    suspend fun getStreak(): StreakEntity? = streakDao.getStreak()

    suspend fun getSyncOverview(): SyncOverview {
        val records = buildList {
            addAll(lessonProgressDao.getAllProgress().map { it.syncStatus to it.lastSyncedAt })
            addAll(userScoreDao.getAllScores().map { it.syncStatus to it.lastSyncedAt })
            streakDao.getStreak()?.let { add(it.syncStatus to it.lastSyncedAt) }
        }
        if (records.isEmpty()) return SyncOverview(SyncStatus.NOT_SYNCED, null, 0)
        val statuses = records.map { it.first }
        val state = when {
            statuses.any { it == SyncStatus.FAILED.name } -> SyncStatus.FAILED
            statuses.any { it == SyncStatus.SYNCING.name } -> SyncStatus.SYNCING
            statuses.all { it == SyncStatus.SYNCED.name } -> SyncStatus.SYNCED
            else -> SyncStatus.NOT_SYNCED
        }
        return SyncOverview(
            status = state,
            lastSyncedAt = records.mapNotNull { it.second }.maxOrNull(),
            pendingCount = statuses.count { it != SyncStatus.SYNCED.name }
        )
    }

    /** Keeps offline data in a known safe state until a real sync transport is configured. */
    suspend fun markLocalDataNotSynced() {
        lessonProgressDao.updateAllSyncStatus(SyncStatus.NOT_SYNCED.name, null)
        userScoreDao.updateAllSyncStatus(SyncStatus.NOT_SYNCED.name, null)
        streakDao.updateAllSyncStatus(SyncStatus.NOT_SYNCED.name, null)
    }

    suspend fun updateStreak(): StreakEntity {
        val today = LocalDate.now()
        val existing = streakDao.getStreak()
        val next = when {
            existing == null -> StreakEntity(
                id = StreakDao.DEFAULT_STREAK_ID,
                currentStreak = 1,
                longestStreak = 1,
                lastActiveDate = today.toString()
            )
            existing.lastActiveDate == today.toString() -> existing
            isYesterday(existing.lastActiveDate, today) -> {
                val current = existing.currentStreak + 1
                existing.copy(
                    currentStreak = current,
                    longestStreak = max(existing.longestStreak, current),
                    lastActiveDate = today.toString()
                )
            }
            else -> existing.copy(
                currentStreak = 1,
                longestStreak = max(existing.longestStreak, 1),
                lastActiveDate = today.toString()
            )
        }
        streakDao.upsertStreak(next.copy(
            syncStatus = SyncStatus.NOT_SYNCED.name,
            lastSyncedAt = null
        ))
        return next.copy(syncStatus = SyncStatus.NOT_SYNCED.name, lastSyncedAt = null)
    }

    private fun isYesterday(rawDate: String, today: LocalDate): Boolean {
        return runCatching { LocalDate.parse(rawDate) == today.minusDays(1) }.getOrDefault(false)
    }

    companion object {
        @Volatile
        private var INSTANCE: LmsRepository? = null

        fun getInstance(context: Context): LmsRepository {
            return INSTANCE ?: synchronized(this) {
                val database = LmsDatabase.getInstance(context)
                INSTANCE ?: LmsRepository(
                    lessonDao = database.lessonDao(),
                    lessonProgressDao = database.lessonProgressDao(),
                    userScoreDao = database.userScoreDao(),
                    streakDao = database.streakDao()
                ).also { INSTANCE = it }
            }
        }
    }
}
