package com.sciobraille.scanner.lms

/** Local records are always persisted before an optional cloud sync is attempted. */
enum class SyncStatus {
    NOT_SYNCED,
    SYNCING,
    SYNCED,
    FAILED
}

data class SyncResult(
    val status: SyncStatus,
    val message: String,
    val uploadedCount: Int = 0,
    val failedCount: Int = 0,
    val lastSyncedAt: Long? = null
)

data class SyncOverview(
    val status: SyncStatus,
    val lastSyncedAt: Long?,
    val pendingCount: Int
)
