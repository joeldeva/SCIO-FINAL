package com.sciobraille.scanner.tools
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.*
import org.junit.Test
class TranslationNetworkTest {
 @Test fun unicodeAndSourceArePreservedOverHttp() = runBlocking {
  val server=MockWebServer();server.start()
  try {
   server.enqueue(MockResponse().setHeader("Content-Type","application/json").setBody("""{"ok":true,"text":"வணக்கம்!"}"""))
   val result=TranslationRepository(OkHttpClient(),server.url("/").toString()).translate("Hello!",targetLanguage=AppLanguage.TAMIL)
   assertTrue(result is TranslationResult.Success);assertEquals("வணக்கம்!",(result as TranslationResult.Success).translatedText);assertEquals("Hello!",result.sourceText)
   assertEquals("/api/translate",server.takeRequest().path)
  } finally {server.shutdown()}
 }
 @Test fun offlineOnlyNeverCallsBackend() = runBlocking {
  val server=MockWebServer();server.start()
  try {
   val result=TranslationRepository(OkHttpClient(),server.url("/").toString(),onlineAllowed={false}).translate("Hello",targetLanguage=AppLanguage.TAMIL)
   assertEquals(TranslationResult.OfflineUnavailable,result);assertEquals(0,server.requestCount)
  } finally {server.shutdown()}
 }
 @Test fun providerErrorDoesNotBecomeSuccessfulTranslation() = runBlocking {
  val server=MockWebServer();server.start()
  try {
   server.enqueue(MockResponse().setResponseCode(503).setBody("""{"ok":false,"error":"Provider unavailable"}"""))
   val result=TranslationRepository(OkHttpClient(),server.url("/").toString()).translate("Hello",targetLanguage=AppLanguage.HINDI)
   assertTrue(result is TranslationResult.Failure)
   server.enqueue(MockResponse().setBody("""{"ok":true,"text":"नमस्ते"}"""))
   assertTrue(TranslationRepository(OkHttpClient(),server.url("/").toString()).translate("Hello",targetLanguage=AppLanguage.HINDI) is TranslationResult.Success)
  } finally {server.shutdown()}
 }
}
