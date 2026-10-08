package com.sciobraille.scanner.tools

import android.graphics.Bitmap
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions

class StoryTextRecognizer : AutoCloseable {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

    fun recognize(
        bitmap: Bitmap,
        onSuccess: (String) -> Unit,
        onFailure: (Throwable) -> Unit
    ) {
        recognizer.process(InputImage.fromBitmap(bitmap, 0))
            .addOnSuccessListener { result -> onSuccess(result.text.trim()) }
            .addOnFailureListener(onFailure)
    }

    override fun close() {
        recognizer.close()
    }
}
