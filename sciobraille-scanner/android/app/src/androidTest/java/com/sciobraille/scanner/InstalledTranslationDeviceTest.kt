package com.sciobraille.scanner

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.sciobraille.scanner.tools.AppLanguage
import com.sciobraille.scanner.tools.MlKitTranslationFallback
import com.sciobraille.scanner.tools.TranslationRepository
import com.sciobraille.scanner.tools.TranslationResult
import com.sciobraille.scanner.tools.TranslationSource
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okhttp3.OkHttpClient
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeNoException
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/** Live download probe, followed by actual local inference. No fixed translation fixture. */
@RunWith(AndroidJUnit4::class)
class InstalledTranslationDeviceTest {
    @Test fun downloadsTamilThenTranslatesInAppOfflineOnlyMode() = runBlocking {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val report=File(context.filesDir,"installed-translation-smoke.json")
        val local=MlKitTranslationFallback()
        try {
            withTimeout(180_000) { local.download(AppLanguage.TAMIL) }
        } catch(error:Exception) {
            // External model availability is a release gate, not a mocked pass.
            report.writeText(JSONObject().put("status","download_unavailable")
                .put("error_type",error.javaClass.simpleName).put("error",error.message).toString(2))
            assumeNoException("Live ML Kit model could not be downloaded; see report",error)
            return@runBlocking
        }
        assertTrue("Tamil model must be installed", "ta" in local.installedCodes())
        val repository=TranslationRepository(OkHttpClient(),"http://127.0.0.1:1",local,onlineAllowed={false})
        val source="Welcome. Learning Braille connects us."
        val result=withTimeout(30_000) { repository.translate(source,targetLanguage=AppLanguage.TAMIL) }
        assertTrue("Installed model must return a real translation: $result",result is TranslationResult.Success)
        result as TranslationResult.Success
        assertEquals(TranslationSource.LOCAL,result.source)
        assertEquals(source,result.sourceText)
        assertTrue("Output must contain Tamil script",result.translatedText.any { it in '\u0B80'..'\u0BFF' })
        report.writeText(JSONObject().put("status","local_response_received")
            .put("source",source).put("translated",result.translatedText).put("target","ta")
            .put("scope","Actual downloaded ML Kit model; app backend disabled. Not a human quality assessment or packet-capture test.").toString(2))
    }
}
