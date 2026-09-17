package com.sciobraille.scanner.lms

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface LessonProgressDao {
    @Query("SELECT * FROM lesson_progress WHERE lessonId = :lessonId LIMIT 1")
    suspend fun getProgressForLesson(lessonId: String): LessonProgressEntity?

    @Query("SELECT * FROM lesson_progress")
    suspend fun getAllProgress(): List<LessonProgressEntity>

    @Query("SELECT * FROM lesson_progress WHERE syncStatus != 'SYNCED'")
    suspend fun getPendingSync(): List<LessonProgressEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertProgress(progress: LessonProgressEntity)

    @Query("UPDATE lesson_progress SET syncStatus = :status, lastSyncedAt = :lastSyncedAt")
    suspend fun updateAllSyncStatus(status: String, lastSyncedAt: Long?)

    @Query("UPDATE lesson_progress SET syncStatus = :status, lastSyncedAt = :lastSyncedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, status: String, lastSyncedAt: Long?)
}
