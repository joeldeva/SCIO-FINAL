package com.sciobraille.scanner.tools

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

sealed interface TranslationResult {
    data class Success(
        val sourceText: String,
        val translatedText: String,
        val targetLanguage: AppLanguage,
        val source: TranslationSource = TranslationSource.BACKEND
    ) : TranslationResult
    data class Failure(val message: String) : TranslationResult
    data object OfflineUnavailable : TranslationResult
    data object UnsupportedLanguage : TranslationResult
}

enum class TranslationSource { BACKEND, LOCAL }

class TranslationRepository(
    private val httpClient: OkHttpClient,
    private val backendUrl: String,
    private val localFallback: MlKitTranslationFallback? = null
) {
    suspend fun translate(
        text: String,
        sourceLanguage: AppLanguage = AppLanguage.ENGLISH,
        targetLanguage: AppLanguage
    ): TranslationResult = withContext(Dispatchers.IO) {
        val source = text.trim()
        if (source.isBlank()) return@withContext TranslationResult.Failure("Recognized text is empty")
        if (sourceLanguage != AppLanguage.ENGLISH) return@withContext TranslationResult.UnsupportedLanguage
        if (targetLanguage == AppLanguage.ENGLISH) {
            return@withContext TranslationResult.Success(source, source, targetLanguage, TranslationSource.LOCAL)
        }
        val body = requestJson(source, targetLanguage).toRequestBody(JSON_MEDIA_TYPE)
        val request = Request.Builder()
            .url(backendUrl.trimEnd('/') + "/api/translate")
            .post(body)
            .build()
        try {
            httpClient.newCall(request).execute().use { response ->
                val raw = response.body?.string().orEmpty()
                val json = runCatching { JSONObject(raw) }.getOrNull()
                if (!response.isSuccessful || json?.optBoolean("ok", false) != true) {
                    return@withContext localFallback?.translate(source, targetLanguage)
                        ?: TranslationResult.Failure(
                            json?.optString("error")?.takeIf { it.isNotBlank() }
                                ?: "Translation service failed"
                        )
                }
                val translated = json.optString("text").trim()
                if (translated.isBlank()) TranslationResult.Failure("Translation returned no text")
                else TranslationResult.Success(source, translated, targetLanguage, TranslationSource.BACKEND)
            }
        } catch (_: IOException) {
            localFallback?.translate(source, targetLanguage) ?: TranslationResult.OfflineUnavailable
        } catch (_: Exception) {
            localFallback?.translate(source, targetLanguage) ?: TranslationResult.Failure("Translation failed")
        }
    }

    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()

        fun requestJson(text: String, targetLanguage: AppLanguage): String = JSONObject()
            .put("text", text)
            .put("source_lang", AppLanguage.ENGLISH.backendCode)
            .put("target_lang", targetLanguage.backendCode)
            .toString()
    }
}
