package com.sciobraille.scanner.lms

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "streaks")
data class StreakEntity(
    @PrimaryKey val id: String,
    val currentStreak: Int,
    val longestStreak: Int,
    val lastActiveDate: String,
    val syncStatus: String = SyncStatus.NOT_SYNCED.name,
    val lastSyncedAt: Long? = null
)
