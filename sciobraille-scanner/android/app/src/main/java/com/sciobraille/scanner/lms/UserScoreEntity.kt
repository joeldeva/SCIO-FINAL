package com.sciobraille.scanner.lms

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "user_scores",
    indices = [
        Index(value = ["lessonId"]),
        Index(value = ["questionId"])
    ]
)
data class UserScoreEntity(
    @PrimaryKey val id: String,
    val lessonId: String,
    val questionId: String,
    val userAnswer: String,
    val correctAnswer: String,
    val isCorrect: Boolean,
    val timestamp: Long,
    val syncStatus: String = SyncStatus.NOT_SYNCED.name,
    val lastSyncedAt: Long? = null
)
