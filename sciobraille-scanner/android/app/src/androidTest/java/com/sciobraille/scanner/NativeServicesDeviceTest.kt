package com.sciobraille.scanner

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** Runs native Android services; no mocked model, PDF implementation or output. */
@RunWith(AndroidJUnit4::class)
class NativeServicesDeviceTest {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()

    @Test fun unicodeCertificateExportsMultipleRenderablePages() {
        val context = instrumentation.targetContext
        val file = File(context.filesDir, "certificate-device-test.pdf")
        val text = "Presented to\nதமிழ் learner • हिन्दी • العربية • 中文\n\n" +
            (1..120).joinToString("\n") { "Lesson $it completed — Braille learning" }
        file.outputStream().use { CertificatePdf.write(text, it) }
        assertTrue(file.length() > 1000)
        file.inputStream().use { val header=ByteArray(4);assertEquals(4,it.read(header));assertEquals("%PDF",String(header,Charsets.US_ASCII)) }
        ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY).use { descriptor ->
            PdfRenderer(descriptor).use { renderer ->
                assertTrue("Long names/content must paginate", renderer.pageCount > 1)
                for (index in 0 until renderer.pageCount) {
                    renderer.openPage(index).use { page ->
                        val bitmap = Bitmap.createBitmap(page.width, page.height, Bitmap.Config.ARGB_8888)
                        bitmap.eraseColor(Color.WHITE)
                        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                        var ink = 0
                        for (y in 0 until bitmap.height step 4) for (x in 0 until bitmap.width step 4) {
                            if (bitmap.getPixel(x,y) != Color.WHITE) ink++
                        }
                        assertTrue("Export page must contain visible content", ink > 100)
                        bitmap.recycle()
                    }
                }
            }
        }
    }

    @Test fun bundledModelRecognizesPhysicalPhotographOnAndroid() {
        val context = instrumentation.targetContext
        val image = File(context.cacheDir, "physical-braille.jpeg")
        instrumentation.context.assets.open("test_sciobraille.jpeg").use { input ->
            image.outputStream().use { input.copyTo(it) }
        }
        val modelHash = context.assets.open(BuildConfig.OFFLINE_MODEL_ASSET).use {
            MessageDigest.getInstance("SHA-256").digest(it.readBytes()).joinToString("") { b -> "%02x".format(b.toInt() and 255) }
        }
        assertEquals("7e5cf70ecb47f868d69623c7eec8cbd25bc8a547ab242318f1e4a2450fb5561c", modelHash)
        val detector = OfflineBrailleDetector(context)
        try {
            val start = android.os.SystemClock.elapsedRealtime()
            val result = detector.detect(image, mirror = false)
            val elapsed = android.os.SystemClock.elapsedRealtime() - start
            assertTrue(result.ok)
            assertEquals("offline", result.sourceMode)
            assertTrue("Real photograph should produce cells", result.detections > 0)
            assertTrue(result.rawText.isNotBlank())
            assertTrue(result.confidence.isFinite())
            assertTrue(result.boxes.all { it.x1 in 0f..1f && it.x2 in 0f..1f && it.y1 in 0f..1f && it.y2 in 0f..1f })
            File(context.filesDir,"offline-device-smoke.json").writeText(JSONObject()
                .put("scope","Android emulator, real bundled model and repository photograph; not physical-phone accuracy or latency")
                .put("model_sha256",modelHash).put("raw_text",result.rawText)
                .put("detections",result.detections).put("confidence",result.confidence)
                .put("elapsed_ms",elapsed).toString(2))
        } finally { detector.closeIfOpened(); image.delete() }
    }
}
