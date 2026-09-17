package com.sciobraille.scanner.lms

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface StreakDao {
    @Query("SELECT * FROM streaks WHERE id = :id LIMIT 1")
    suspend fun getStreak(id: String = DEFAULT_STREAK_ID): StreakEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertStreak(streak: StreakEntity)

    @Query("UPDATE streaks SET syncStatus = :status, lastSyncedAt = :lastSyncedAt")
    suspend fun updateAllSyncStatus(status: String, lastSyncedAt: Long?)

    @Query("UPDATE streaks SET syncStatus = :status, lastSyncedAt = :lastSyncedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, status: String, lastSyncedAt: Long?)

    companion object {
        const val DEFAULT_STREAK_ID = "default"
    }
}
