package com.sciobraille.scanner.lms

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/** Uploads local-first LMS records using the app's existing OkHttp client. */
class SyncManager(
    private val context: Context,
    private val repository: LmsRepository,
    private val httpClient: OkHttpClient,
    private val backendUrl: String,
    private val userId: String,
    private val canCloudSync: () -> Boolean
) {
    private val syncMutex = Mutex()

    suspend fun syncProgress(): SyncResult = syncMutex.withLock { syncProgressLocked() }

    suspend fun syncScores(): SyncResult = syncMutex.withLock { syncScoresLocked() }

    suspend fun syncStreaks(): SyncResult = syncMutex.withLock { syncStreaksLocked() }

    suspend fun syncAll(): SyncResult = syncMutex.withLock {
        if (!canAttemptSync()) return@withLock unavailableResult()
        val results = listOf(syncProgressLocked(), syncScoresLocked(), syncStreaksLocked())
        val failed = results.sumOf { it.failedCount }
        val uploaded = results.sumOf { it.uploadedCount }
        when {
            failed > 0 -> SyncResult(SyncStatus.FAILED, "Sync failed. Try again.", uploaded, failed)
            uploaded > 0 -> SyncResult(SyncStatus.SYNCED, "Synced", uploaded, 0, System.currentTimeMillis())
            else -> SyncResult(SyncStatus.SYNCED, "Synced", 0, 0, System.currentTimeMillis())
        }
    }

    private suspend fun syncProgressLocked(): SyncResult {
        if (!canAttemptSync()) return unavailableResult()
        var uploaded = 0
        var failed = 0
        repository.getProgressPendingSync().forEach { record ->
            repository.updateProgressSyncStatus(record.id, SyncStatus.SYNCING, null)
            val body = JSONObject().apply {
                put("userId", userId)
                put("lessonId", record.lessonId)
                put("level", record.level)
                put("status", record.status)
                put("score", record.score)
                put("accuracy", record.accuracy / 100.0)
                record.completedAt?.let { put("completedAt", it) }
            }
            if (postJson("/api/progress", body)) {
                repository.updateProgressSyncStatus(record.id, SyncStatus.SYNCED, System.currentTimeMillis())
                uploaded++
            } else {
                repository.updateProgressSyncStatus(record.id, SyncStatus.FAILED, null)
                failed++
            }
        }
        return operationResult(uploaded, failed)
    }

    private suspend fun syncScoresLocked(): SyncResult {
        if (!canAttemptSync()) return unavailableResult()
        var uploaded = 0
        var failed = 0
        repository.getScoresPendingSync().forEach { record ->
            repository.updateScoreSyncStatus(record.id, SyncStatus.SYNCING, null)
            val body = JSONObject().apply {
                put("id", record.id)
                put("userId", userId)
                put("lessonId", record.lessonId)
                put("questionId", record.questionId)
                put("userAnswer", record.userAnswer)
                put("correctAnswer", record.correctAnswer)
                put("isCorrect", record.isCorrect)
                put("timestamp", record.timestamp)
            }
            if (postJson("/api/scores", body)) {
                repository.updateScoreSyncStatus(record.id, SyncStatus.SYNCED, System.currentTimeMillis())
                uploaded++
            } else {
                repository.updateScoreSyncStatus(record.id, SyncStatus.FAILED, null)
                failed++
            }
        }
        return operationResult(uploaded, failed)
    }

    private suspend fun syncStreaksLocked(): SyncResult {
        if (!canAttemptSync()) return unavailableResult()
        val record = repository.getStreakPendingSync() ?: return operationResult(0, 0)
        if (record.syncStatus == SyncStatus.SYNCED.name) return operationResult(0, 0)
        repository.updateStreakSyncStatus(record.id, SyncStatus.SYNCING, null)
        val body = JSONObject().apply {
            put("userId", userId)
            put("currentStreak", record.currentStreak)
            put("longestStreak", record.longestStreak)
            put("lastActiveDate", record.lastActiveDate)
        }
        return if (postJson("/api/streaks", body)) {
            val now = System.currentTimeMillis()
            repository.updateStreakSyncStatus(record.id, SyncStatus.SYNCED, now)
            SyncResult(SyncStatus.SYNCED, "Synced", 1, 0, now)
        } else {
            repository.updateStreakSyncStatus(record.id, SyncStatus.FAILED, null)
            SyncResult(SyncStatus.FAILED, "Sync failed. Try again.", 0, 1)
        }
    }

    private fun postJson(path: String, json: JSONObject): Boolean = runCatching {
        val request = Request.Builder()
            .url(backendUrl.trimEnd('/') + path)
            .post(json.toString().toRequestBody("application/json; charset=utf-8".toMediaType()))
            .build()
        httpClient.newCall(request).execute().use { it.isSuccessful }
    }.getOrDefault(false)

    private fun operationResult(uploaded: Int, failed: Int): SyncResult = when {
        failed > 0 -> SyncResult(SyncStatus.FAILED, "Sync failed. Try again.", uploaded, failed)
        uploaded > 0 -> SyncResult(SyncStatus.SYNCED, "Synced", uploaded, 0, System.currentTimeMillis())
        else -> SyncResult(SyncStatus.SYNCED, "Synced", 0, 0, System.currentTimeMillis())
    }

    private fun unavailableResult(): SyncResult = SyncResult(
        SyncStatus.NOT_SYNCED,
        "Progress saved on this device. It will sync when internet is available."
    )

    private fun canAttemptSync(): Boolean = canCloudSync() && isBackendConfigured() && hasInternetConnection()

    private fun isBackendConfigured(): Boolean = backendUrl.startsWith("http") &&
        !backendUrl.contains("replace-with-your-sciobraille-backend", ignoreCase = true)

    private fun hasInternetConnection(): Boolean {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }
}
