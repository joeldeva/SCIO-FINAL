package com.sciobraille.scanner.tools

import com.google.android.gms.tasks.Task
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.TranslateRemoteModel
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/** Download is explicit; translate never silently downloads a model. */
class MlKitTranslationFallback {
    fun supports(language: AppLanguage) = language.offlineCode?.let { TranslateLanguage.fromLanguageTag(it) } != null
    suspend fun installedCodes(): Set<String> = RemoteModelManager.getInstance()
        .getDownloadedModels(TranslateRemoteModel::class.java).awaitResult().map { it.language }.toSet()
    suspend fun download(language: AppLanguage) {
        val translator = translator(language)
        try { translator.downloadModelIfNeeded(DownloadConditions.Builder().build()).awaitResult() }
        finally { translator.close() }
    }
    suspend fun delete(language: AppLanguage) {
        val code = language.offlineCode ?: return
        RemoteModelManager.getInstance().deleteDownloadedModel(TranslateRemoteModel.Builder(code).build()).awaitResult()
    }
    suspend fun translate(text: String, targetLanguage: AppLanguage): TranslationResult {
        if (targetLanguage == AppLanguage.ENGLISH) return TranslationResult.Success(text, text, targetLanguage, TranslationSource.LOCAL)
        if (!supports(targetLanguage)) return TranslationResult.UnsupportedLanguage
        if (targetLanguage.offlineCode !in installedCodes()) return TranslationResult.OfflineUnavailable
        val translator = translator(targetLanguage)
        return try {
            val value = translator.translate(text).awaitResult()
            if (value.isBlank()) TranslationResult.Failure("Empty on-device translation")
            else TranslationResult.Success(text, value, targetLanguage, TranslationSource.LOCAL)
        } catch (cancelled: kotlinx.coroutines.CancellationException) { throw cancelled }
        catch (_: Exception) { TranslationResult.Failure("On-device translation failed. Try downloading the model again.") }
        finally { translator.close() }
    }
    private fun translator(language: AppLanguage) = Translation.getClient(TranslatorOptions.Builder()
        .setSourceLanguage(TranslateLanguage.ENGLISH)
        .setTargetLanguage(requireNotNull(TranslateLanguage.fromLanguageTag(requireNotNull(language.offlineCode)))).build())
}
internal suspend fun <T> Task<T>.awaitResult(): T = suspendCancellableCoroutine { continuation ->
    addOnSuccessListener { if (continuation.isActive) continuation.resume(it) }
    addOnFailureListener { if (continuation.isActive) continuation.resumeWithException(it) }
    addOnCanceledListener { continuation.cancel() }
}
