package com.sciobraille.scanner.lms

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface UserScoreDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertScore(score: UserScoreEntity)

    @Query("SELECT * FROM user_scores WHERE lessonId = :lessonId ORDER BY timestamp DESC")
    suspend fun getScoresForLesson(lessonId: String): List<UserScoreEntity>

    @Query("SELECT * FROM user_scores WHERE correctAnswer = :letter ORDER BY timestamp DESC")
    suspend fun getScoresForCorrectAnswer(letter: String): List<UserScoreEntity>

    @Query("SELECT * FROM user_scores ORDER BY timestamp DESC")
    suspend fun getAllScores(): List<UserScoreEntity>

    @Query("SELECT * FROM user_scores WHERE syncStatus != 'SYNCED' ORDER BY timestamp ASC")
    suspend fun getPendingSync(): List<UserScoreEntity>

    @Query("UPDATE user_scores SET syncStatus = :status, lastSyncedAt = :lastSyncedAt")
    suspend fun updateAllSyncStatus(status: String, lastSyncedAt: Long?)

    @Query("UPDATE user_scores SET syncStatus = :status, lastSyncedAt = :lastSyncedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, status: String, lastSyncedAt: Long?)
}
