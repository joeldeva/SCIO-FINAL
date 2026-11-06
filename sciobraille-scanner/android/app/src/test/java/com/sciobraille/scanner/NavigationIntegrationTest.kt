package com.sciobraille.scanner
import android.app.AlertDialog
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.annotation.LooperMode
import org.robolectric.shadows.ShadowAlertDialog
import java.io.File
@RunWith(RobolectricTestRunner::class)
@Config(sdk=[34],qualifiers="w360dp-h800dp-xhdpi")
@LooperMode(LooperMode.Mode.PAUSED)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class NavigationIntegrationTest {
 @Before fun setup() { org.robolectric.Shadows.shadowOf(RuntimeEnvironment.getApplication()).denyPermissions(android.Manifest.permission.CAMERA);RuntimeEnvironment.getApplication().getSharedPreferences("sciobraille",Context.MODE_PRIVATE).edit().putBoolean("onboarded",true).commit() }
 private fun texts(view:View):List<TextView> = buildList { if(view is TextView) add(view);if(view is ViewGroup) for(i in 0 until view.childCount) addAll(texts(view.getChildAt(i))) }
 private fun find(root:View,label:String)=texts(root).first { it.text.toString()==label && it.isShown }
 private fun screenshot(root:View,name:String) {
  root.measure(View.MeasureSpec.makeMeasureSpec(720,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(1600,View.MeasureSpec.EXACTLY));root.layout(0,0,720,1600)
  val bitmap=Bitmap.createBitmap(720,1600,Bitmap.Config.ARGB_8888);root.draw(Canvas(bitmap))
  val file=File("build/reports/screenshots/$name.png");file.parentFile!!.mkdirs();file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG,100,it) };bitmap.recycle()
 }
 @Test fun homeHistoryHelpAndSettingsAreConnected() {
  val controller=Robolectric.buildActivity(MainActivity::class.java).setup().visible();val root=controller.get().window.decorView
  assertTrue(find(root,"Start live scan").isClickable);screenshot(root,"home-light")
  find(root,"Scan").performClick();screenshot(root,"scanner-empty");find(root,"History").performClick();assertTrue(texts(root).any { it.isShown && it.text.startsWith("No scans yet") })
  find(root,"Help").performClick();assertTrue(texts(root).any { it.isShown && it.text.contains("English") })
  find(root,"Settings").performClick();val dialog=ShadowAlertDialog.getLatestAlertDialog();assertTrue(dialog.isShowing);screenshot(dialog.window!!.decorView,"settings")
  assertTrue(texts(dialog.window!!.decorView).any { it.text=="Backend address" });dialog.getButton(AlertDialog.BUTTON_POSITIVE).performClick()
  find(root,"Home").performClick();assertTrue(find(root,"Translate a Braille photo").isClickable);controller.pause().stop().destroy()
 }
 @Test fun darkLargeTextPreferencesPersist() {
  AccessibilityPreferencesStore(RuntimeEnvironment.getApplication()).save(AccessibilityPreferences(theme=ThemePreference.DARK,textSize=TextSizePreference.EXTRA_LARGE,highContrast=true))
  val controller=Robolectric.buildActivity(MainActivity::class.java).setup().visible();val root=controller.get().window.decorView
  root.viewTreeObserver.dispatchOnGlobalLayout();assertTrue(ScioColors.dark);assertTrue(ScioColors.contrast);screenshot(root,"home-dark-large")
  controller.recreate().visible();assertEquals(TextSizePreference.EXTRA_LARGE,AccessibilityPreferencesStore(controller.get()).load().textSize);controller.pause().stop().destroy()
 }
 // Native PdfDocument is not implemented by Robolectric's API 34 runtime.
 // Actual PDF generation is exercised in NativeServicesDeviceTest on Android.
}
