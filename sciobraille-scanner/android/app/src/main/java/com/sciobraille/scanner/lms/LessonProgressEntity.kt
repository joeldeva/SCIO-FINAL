package com.sciobraille.scanner.lms

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

object LessonProgressStatus {
    const val NOT_STARTED = "NOT_STARTED"
    const val IN_PROGRESS = "IN_PROGRESS"
    const val COMPLETED = "COMPLETED"
}

@Entity(
    tableName = "lesson_progress",
    indices = [Index(value = ["lessonId"], unique = true)]
)
data class LessonProgressEntity(
    @PrimaryKey val id: String,
    val lessonId: String,
    val level: Int,
    val status: String,
    val score: Int,
    val accuracy: Float,
    val attempts: Int,
    val completedAt: Long?,
    val updatedAt: Long,
    val syncStatus: String = SyncStatus.NOT_SYNCED.name,
    val lastSyncedAt: Long? = null
)
