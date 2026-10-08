package com.sciobraille.scanner.tools

import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

class MlKitTranslationFallback {
    suspend fun translate(text: String, targetLanguage: AppLanguage): TranslationResult {
        if (targetLanguage == AppLanguage.ENGLISH) {
            return TranslationResult.Success(text, text, targetLanguage, TranslationSource.LOCAL)
        }
        val sourceCode = TranslateLanguage.fromLanguageTag(AppLanguage.ENGLISH.languageCode)
            ?: return TranslationResult.UnsupportedLanguage
        val targetCode = TranslateLanguage.fromLanguageTag(targetLanguage.languageCode)
            ?: return TranslationResult.UnsupportedLanguage
        val translator = Translation.getClient(
            TranslatorOptions.Builder()
                .setSourceLanguage(sourceCode)
                .setTargetLanguage(targetCode)
                .build()
        )
        return suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { translator.close() }
            translator.downloadModelIfNeeded(DownloadConditions.Builder().build())
                .addOnSuccessListener {
                    translator.translate(text)
                        .addOnSuccessListener { translated ->
                            if (continuation.isActive) {
                                continuation.resume(
                                    TranslationResult.Success(text, translated, targetLanguage, TranslationSource.LOCAL)
                                )
                            }
                            translator.close()
                        }
                        .addOnFailureListener {
                            if (continuation.isActive) continuation.resume(TranslationResult.Failure("On-device translation failed"))
                            translator.close()
                        }
                }
                .addOnFailureListener {
                    if (continuation.isActive) continuation.resume(TranslationResult.OfflineUnavailable)
                    translator.close()
                }
        }
    }
}
