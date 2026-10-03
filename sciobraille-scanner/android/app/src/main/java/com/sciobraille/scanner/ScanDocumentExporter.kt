package com.sciobraille.scanner

import java.text.DateFormat
import java.util.Date

data class ScanDocument(
    val id: String,
    val title: String,
    val createdAt: Long,
    val rawText: String,
    val displayText: String,
    val correctedText: String,
    val lineCount: Int,
    val detectedCells: Int,
    val averageConfidence: Double,
    val orientation: ScanOrientation,
    val mode: RecognitionMode,
    val sourceType: String,
    val translatedText: String? = null,
    val cells: List<RecognitionCell> = emptyList()
)

object ScanDocumentExporter {
    fun plainText(document: ScanDocument): String {
        require(document.rawText.isNotBlank()) { "Document text is empty" }
        return buildString {
            appendLine("Sciobraille")
            appendLine(document.title.ifBlank { "Braille scan" })
            appendLine(DateFormat.getDateTimeInstance().format(Date(document.createdAt)))
            appendLine()
            appendLine(document.rawText)
            document.translatedText?.takeIf { it.isNotBlank() }?.let {
                appendLine()
                appendLine("Translation")
                appendLine(it)
            }
            appendLine()
            appendLine("Average confidence: ${(document.averageConfidence * 100).toInt()}%")
            appendLine("Orientation: ${document.orientation.name.lowercase()}")
            appendLine("Mode: ${document.mode.name.lowercase()}")
            append("Generated from a physical Braille scan.")
        }
    }

    fun safeFileName(title: String, extension: String): String {
        val base = title.trim().replace(Regex("[^A-Za-z0-9._-]+"), "_").trim('_').take(60)
            .ifBlank { "sciobraille_document" }
        return "$base.${extension.trimStart('.')}"
    }
}
