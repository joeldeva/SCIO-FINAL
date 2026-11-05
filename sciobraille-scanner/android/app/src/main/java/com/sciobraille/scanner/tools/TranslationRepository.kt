package com.sciobraille.scanner.tools

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

sealed interface TranslationResult {
    data class Success(val sourceText: String, val translatedText: String, val targetLanguage: AppLanguage,
        val source: TranslationSource = TranslationSource.BACKEND) : TranslationResult
    data class Failure(val message: String) : TranslationResult
    data object OfflineUnavailable : TranslationResult
    data object UnsupportedLanguage : TranslationResult
}
enum class TranslationSource { BACKEND, LOCAL }
class TranslationRepository(private val httpClient: OkHttpClient, private val backendUrl: String,
    private val localFallback: MlKitTranslationFallback? = null, private val onlineAllowed: () -> Boolean = { true }) {
    suspend fun languages(): Set<String> = withContext(Dispatchers.IO) {
        check(onlineAllowed()) { "Offline mode" }
        val request = Request.Builder().url(backendUrl.trimEnd('/') + "/api/languages").build()
        httpClient.newCall(request).execute().use { response ->
            check(response.isSuccessful)
            val body = JSONObject(response.body?.string().orEmpty()); check(body.optBoolean("ok"))
            val array = body.getJSONArray("languages")
            (0 until array.length()).map { array.getJSONObject(it).getString("code") }.toSet()
        }
    }
    suspend fun translate(text: String, sourceLanguage: AppLanguage = AppLanguage.ENGLISH,
        targetLanguage: AppLanguage): TranslationResult = withContext(Dispatchers.IO) {
        val source = text.trim()
        if (source.isBlank()) return@withContext TranslationResult.Failure("Recognized text is empty")
        if (source.length > 4000) return@withContext TranslationResult.Failure("Translate at most 4000 characters at a time")
        if (sourceLanguage != AppLanguage.ENGLISH) return@withContext TranslationResult.UnsupportedLanguage
        if (targetLanguage == AppLanguage.ENGLISH) return@withContext TranslationResult.Success(source, source, targetLanguage, TranslationSource.LOCAL)
        val local = try { localFallback?.translate(source, targetLanguage) }
        catch (cancelled: CancellationException) { throw cancelled }
        catch (_: Exception) { null }
        if (local is TranslationResult.Success) return@withContext local
        if (!onlineAllowed()) return@withContext TranslationResult.OfflineUnavailable
        try {
            val request = Request.Builder().url(backendUrl.trimEnd('/') + "/api/translate")
                .post(requestJson(source, targetLanguage).toRequestBody(JSON_MEDIA_TYPE)).build()
            httpClient.newCall(request).execute().use { response ->
                val json = runCatching { JSONObject(response.body?.string().orEmpty()) }.getOrNull()
                if (!response.isSuccessful || json?.optBoolean("ok", false) != true)
                    return@withContext TranslationResult.Failure(json?.optString("error")?.takeIf { it.isNotBlank() }
                        ?: "Translation service unavailable. Download an offline model in Languages.")
                val translated = json.optString("text").trim()
                if (translated.isBlank()) TranslationResult.Failure("Translation returned no text")
                else TranslationResult.Success(source, translated, targetLanguage)
            }
        } catch (cancelled: CancellationException) { throw cancelled }
        catch (_: IOException) { TranslationResult.OfflineUnavailable }
        catch (_: Exception) { TranslationResult.Failure("Translation failed. Check backend settings.") }
    }
    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
        fun requestJson(text: String, targetLanguage: AppLanguage): String = JSONObject().put("text", text)
            .put("source_lang", AppLanguage.ENGLISH.backendCode).put("target_lang", targetLanguage.backendCode).toString()
    }
}
