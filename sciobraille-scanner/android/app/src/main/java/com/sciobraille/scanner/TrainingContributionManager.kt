package com.sciobraille.scanner

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.UUID
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

private const val CONTRIBUTION_SCHEMA_VERSION = 2
const val CONTRIBUTION_CONSENT_VERSION = "2026-11-19-v2"
private const val EXPORT_MAX_AGE_MS = 24L * 60L * 60L * 1000L

internal object ContributionGeometry {
    fun modelFacingBoxes(boxes: List<DetectionBox>, mirrored: Boolean): List<DetectionBox> =
        if (!mirrored) boxes else boxes.map { box ->
            box.copy(x1 = 1f - box.x2, x2 = 1f - box.x1)
        }
}

data class ContributionExport(
    val id: String,
    val archive: File
)

private data class PendingContribution(
    val image: File,
    val payload: ScannerPayload,
    val capturedAt: Long,
    val width: Int,
    val height: Int
)

/**
 * Builds user-initiated, offline contribution archives. Nothing is uploaded by
 * this class; Android's share sheet transfers a package only after consent.
 */
class TrainingContributionManager(private val context: Context) {
    private val root = File(context.cacheDir, "training_contributions")
    private var pending: PendingContribution? = null

    init {
        root.mkdirs()
        pruneExpiredExports()
    }

    @Synchronized
    fun hasPending(): Boolean = pending?.image?.isFile == true

    @Synchronized
    fun rememberModelInput(source: File, payload: ScannerPayload): Boolean {
        clearPending()
        val decoded = BitmapFactory.decodeFile(source.absolutePath) ?: return false
        val modelFacing = if (payload.inputFlippedHorizontal) {
            Bitmap.createBitmap(
                decoded,
                0,
                0,
                decoded.width,
                decoded.height,
                Matrix().apply { preScale(-1f, 1f) },
                true
            )
        } else {
            decoded
        }
        val image = File(root, "pending-model-input.jpg")
        val written = runCatching {
            FileOutputStream(image).use { stream ->
                check(modelFacing.compress(Bitmap.CompressFormat.JPEG, 92, stream))
            }
            image.length() > 0L
        }.getOrDefault(false)
        val width = modelFacing.width
        val height = modelFacing.height
        if (modelFacing !== decoded) modelFacing.recycle()
        decoded.recycle()
        if (!written) {
            image.delete()
            return false
        }
        pending = PendingContribution(image, payload, System.currentTimeMillis(), width, height)
        return true
    }

    @Synchronized
    fun createAnnotatedPreview(maxDimension: Int = 1_280): Bitmap? {
        val source = pending?.takeIf { it.image.isFile } ?: return null
        return renderAnnotatedImage(source, maxDimension)
    }

    @Synchronized
    fun createAnnotatedImageExport(): File {
        val source = pending?.takeIf { it.image.isFile }
            ?: error("No processed scan is available")
        val bitmap = renderAnnotatedImage(source, 2_048)
            ?: error("Could not create annotated image")
        val output = File(root, "sciobraille-annotated-${System.currentTimeMillis()}.jpg")
        FileOutputStream(output).use { stream ->
            check(bitmap.compress(Bitmap.CompressFormat.JPEG, 94, stream))
        }
        bitmap.recycle()
        return output
    }

    @Synchronized
    fun createExport(
        correctedText: String,
        notes: String,
        publicationScope: ContributionPublicationScope
    ): ContributionExport {
        val source = pending?.takeIf { it.image.isFile }
            ?: error("No processed scan is available")
        val groundTruth = correctedText.trim().take(2_000)
        require(groundTruth.isNotBlank()) { "Corrected text is required" }

        val id = UUID.randomUUID().toString()
        val archive = File(root, "sciobraille-contribution-${id.take(8)}.zip")
        val imageHash = sha256(source.image)
        val modelHash = context.assets.open(BuildConfig.OFFLINE_MODEL_ASSET).use(::sha256)
        val modelBoxes = ContributionGeometry.modelFacingBoxes(
            source.payload.boxes,
            source.payload.inputFlippedHorizontal
        )

        val metadata = JSONObject().apply {
            put("schema_version", CONTRIBUTION_SCHEMA_VERSION)
            put("contribution_id", id)
            put("created_at_epoch_ms", source.capturedAt)
            put("language", "en")
            put("braille_grade", 1)
            put("image_file", "image.jpg")
            put("image_width", source.width)
            put("image_height", source.height)
            put("image_sha256", imageHash)
            put("model_asset", BuildConfig.OFFLINE_MODEL_ASSET)
            put("model_sha256", modelHash)
            put("app_version", BuildConfig.VERSION_NAME)
            put("app_version_code", BuildConfig.VERSION_CODE)
            put("raw_model_text", source.payload.rawText.ifBlank { source.payload.text })
            put("user_corrected_text", groundTruth)
            put("notes", notes.trim().take(1_000))
            put("average_confidence", source.payload.confidence)
            put("detection_count", source.payload.detections)
            put("input_flipped_horizontal", source.payload.inputFlippedHorizontal)
            put("coordinate_space", "normalized_model_facing_image")
            put("requires_manual_box_review", true)
            put("publication_scope", publicationScope.metadataValue)
            put("predicted_boxes", JSONArray().apply {
                modelBoxes.forEach { box ->
                    put(JSONObject().apply {
                        put("label", box.label)
                        put("class_id", box.label.singleOrNull()?.lowercaseChar()?.let { it - 'a' } ?: -1)
                        put("confidence", box.confidence)
                        put("x1", box.x1)
                        put("y1", box.y1)
                        put("x2", box.x2)
                        put("y2", box.y2)
                    })
                }
            })
            put("consent", JSONObject().apply {
                put("version", CONTRIBUTION_CONSENT_VERSION)
                put("affirmative", true)
                put("adult_or_authorized_representative", true)
                put("no_sensitive_content_confirmed", true)
                put("public_dataset_release", publicationScope == ContributionPublicationScope.PUBLIC_DATASET)
                put("approved_uses", JSONArray(buildList {
                    add("research")
                    add("manual_annotation")
                    add("model_training")
                    add("model_evaluation")
                    add("model_distribution")
                    if (publicationScope == ContributionPublicationScope.PUBLIC_DATASET) {
                        add("public_dataset_release")
                    }
                }))
            })
        }

        ZipOutputStream(FileOutputStream(archive)).use { zip ->
            zip.putNextEntry(ZipEntry("image.jpg"))
            source.image.inputStream().use { it.copyTo(zip) }
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("metadata.json"))
            zip.write(metadata.toString(2).toByteArray(Charsets.UTF_8))
            zip.closeEntry()
            zip.putNextEntry(ZipEntry("README.txt"))
            zip.write(
                ("Sciobraille voluntary contribution $id\n" +
                    "Publication scope: ${publicationScope.metadataValue}\n").toByteArray(Charsets.UTF_8)
            )
            zip.closeEntry()
        }
        return ContributionExport(id, archive)
    }

    @Synchronized
    fun clearPending() {
        pending?.image?.delete()
        pending = null
        File(root, "pending-model-input.jpg").delete()
    }

    private fun pruneExpiredExports(now: Long = System.currentTimeMillis()) {
        root.listFiles()
            ?.filter {
                val disposableExport = it.extension.equals("zip", ignoreCase = true) ||
                    (it.extension.equals("jpg", ignoreCase = true) && it.name.startsWith("sciobraille-annotated-"))
                disposableExport && now - it.lastModified() > EXPORT_MAX_AGE_MS
            }
            ?.forEach(File::delete)
    }

    private fun renderAnnotatedImage(source: PendingContribution, maxDimension: Int): Bitmap? {
        val decoded = BitmapFactory.decodeFile(source.image.absolutePath) ?: return null
        val scale = minOf(1f, maxDimension.toFloat() / maxOf(decoded.width, decoded.height).toFloat())
        val width = (decoded.width * scale).toInt().coerceAtLeast(1)
        val height = (decoded.height * scale).toInt().coerceAtLeast(1)
        val output = Bitmap.createScaledBitmap(decoded, width, height, true)
            .copy(Bitmap.Config.ARGB_8888, true)
        if (decoded !== output) decoded.recycle()

        val stroke = (maxOf(width, height) * 0.004f).coerceIn(3f, 10f)
        val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(0, 180, 90)
            style = Paint.Style.STROKE
            strokeWidth = stroke
        }
        val labelSize = (maxOf(width, height) * 0.035f).coerceIn(24f, 60f)
        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textSize = labelSize
            typeface = Typeface.DEFAULT_BOLD
        }
        val labelBackground = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(215, 0, 90, 55)
            style = Paint.Style.FILL
        }
        val boxes = ContributionGeometry.modelFacingBoxes(
            source.payload.boxes,
            source.payload.inputFlippedHorizontal
        )
        Canvas(output).apply {
            boxes.forEach { box ->
                val rect = RectF(
                    box.x1.coerceIn(0f, 1f) * width,
                    box.y1.coerceIn(0f, 1f) * height,
                    box.x2.coerceIn(0f, 1f) * width,
                    box.y2.coerceIn(0f, 1f) * height
                )
                drawRect(rect, boxPaint)
                val label = "${box.label} ${(box.confidence * 100).toInt()}%"
                val textWidth = labelPaint.measureText(label)
                val labelTop = (rect.top - labelSize - stroke).coerceAtLeast(0f)
                drawRoundRect(
                    RectF(rect.left, labelTop, rect.left + textWidth + stroke * 3, labelTop + labelSize + stroke),
                    stroke,
                    stroke,
                    labelBackground
                )
                drawText(label, rect.left + stroke, labelTop + labelSize * 0.82f, labelPaint)
            }
        }
        return output
    }

    private fun sha256(file: File): String = FileInputStream(file).use(::sha256)

    private fun sha256(input: java.io.InputStream): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            digest.update(buffer, 0, read)
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
