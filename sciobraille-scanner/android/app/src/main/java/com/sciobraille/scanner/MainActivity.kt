package com.sciobraille.scanner

import android.Manifest
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.sciobraille.scanner.lms.BrailleCellView
import com.sciobraille.scanner.lms.BrailleMappings
import com.sciobraille.scanner.lms.EntitlementManager
import com.sciobraille.scanner.lms.Grade2Contraction
import com.sciobraille.scanner.lms.Grade2Contractions
import com.sciobraille.scanner.lms.LessonContent
import com.sciobraille.scanner.lms.LessonEntity
import com.sciobraille.scanner.lms.LessonProgressEntity
import com.sciobraille.scanner.lms.LessonProgressStatus
import com.sciobraille.scanner.lms.Language
import com.sciobraille.scanner.lms.LmsAudioManager
import com.sciobraille.scanner.lms.LmsHapticManager
import com.sciobraille.scanner.lms.LmsRepository
import com.sciobraille.scanner.lms.LmsProgressRules
import com.sciobraille.scanner.lms.MilestoneAward
import com.sciobraille.scanner.lms.MilestoneManager
import com.sciobraille.scanner.lms.SyncManager
import com.sciobraille.scanner.lms.SyncOverview
import com.sciobraille.scanner.lms.SyncStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString.Companion.toByteString
import org.json.JSONArray
import org.json.JSONObject
import org.tensorflow.lite.DataType
import org.tensorflow.lite.Interpreter
import java.io.File
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.text.DateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.random.Random

private const val CAMERA_PERMISSION_REQUEST = 42
private const val SCAN_INTERVAL_MS = 350L
private const val MAX_IN_FLIGHT_FRAMES = 2
private const val SOCKET_RESPONSE_TIMEOUT_MS = 5_000L
private const val FALLBACK_IMAGE_SIZE = 640
private const val FALLBACK_CONFIDENCE = 0.35
private const val FALLBACK_DUPLICATE_IOU = 0.70
private const val FALLBACK_SPACE_GAP_MULTIPLIER = 1.8
private const val FALLBACK_SPACE_WIDTH_MULTIPLIER = 1.35
private const val FALLBACK_HISTORY_SIZE = 5

private object ScioColors {
    const val BACKGROUND = 0xFFFCF9F8.toInt()
    const val SURFACE = 0xFFFFFFFF.toInt()
    const val SURFACE_CONTAINER = 0xFFF0EDED.toInt()
    const val SURFACE_HIGH = 0xFFEAE7E7.toInt()
    const val TEXT = 0xFF1C1B1B.toInt()
    const val MUTED = 0xFF474552.toInt()
    const val OUTLINE = 0xFFC8C4D4.toInt()
    const val PRIMARY = 0xFF584FB9.toInt()
    const val PRIMARY_CONTAINER = 0xFF7169D4.toInt()
    const val PRIMARY_FIXED = 0xFFE3DFFF.toInt()
    const val SECONDARY = 0xFF8B4F31.toInt()
    const val SECONDARY_CONTAINER = 0xFFFDAF8A.toInt()
    const val SECONDARY_FIXED = 0xFFFFDBCC.toInt()
    const val DARK = 0xFF313030.toInt()
    const val ERROR = 0xFFBA1A1A.toInt()
}

class MainActivity : ComponentActivity(), TextToSpeech.OnInitListener {
    private lateinit var contentHost: FrameLayout
    private lateinit var scannerScreen: View
    private lateinit var historyScreen: View
    private lateinit var learnScreen: View
    private lateinit var aboutScreen: View
    private lateinit var previewView: PreviewView
    private lateinit var detectionOverlay: DetectionOverlayView
    private lateinit var frameOverlay: ScanFrameOverlayView
    private lateinit var outputText: TextView
    private lateinit var braillePreviewText: TextView
    private lateinit var statsText: TextView
    private lateinit var scanButton: Button
    private lateinit var flashButton: Button
    private lateinit var progress: ProgressBar
    private lateinit var historyList: LinearLayout
    private lateinit var learnTitleText: TextView
    private lateinit var learnSubtitleText: TextView
    private lateinit var learnLanguageButton: Button
    private lateinit var learnStatusText: TextView
    private lateinit var learnList: LinearLayout
    private lateinit var scannerNav: TextView
    private lateinit var historyNav: TextView
    private lateinit var learnNav: TextView
    private lateinit var aboutNav: TextView

    private val mainHandler = Handler(Looper.getMainLooper())
    private val networkExecutor = Executors.newSingleThreadExecutor()
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(6, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private var camera: Camera? = null
    private var imageCapture: ImageCapture? = null
    private var webSocket: WebSocket? = null
    private var isScanning = false
    private var isFrameInFlight = false
    private var pendingFrames = 0
    private var pendingSinceMs = 0L
    private var lastSocketAttemptMs = 0L
    private var torchOn = false
    private var lastOutput = ""
    private var lastHistoryText = ""
    private var currentTab = AppTab.SCANNER
    private var scanPracticePending = false
    private var scanPracticeLessonId = "level-6-scan-own-page"
    private var textToSpeech: TextToSpeech? = null
    private var isTtsReady = false
    private val historyEntries = mutableListOf<HistoryEntry>()
    private val fallbackDetector by lazy { OfflineBrailleDetector(this) }
    private val lmsRepository by lazy { LmsRepository.getInstance(this) }
    private val lmsAudioManager by lazy { LmsAudioManager { textToSpeech.takeIf { isTtsReady } } }
    private val lmsHapticManager by lazy { LmsHapticManager(this) }
    private val entitlementManager by lazy { EntitlementManager(this) }
    private val milestoneManager by lazy { MilestoneManager(this, lmsRepository) }
    private val syncManager by lazy {
        SyncManager(
            this,
            lmsRepository,
            httpClient,
            BuildConfig.SCIOBRAILLE_BACKEND_URL,
            lmsSyncUserId(),
            canCloudSync = { entitlementManager.canUseCloudSync() }
        )
    }

    private val scanLoop = object : Runnable {
        override fun run() {
            if (!isScanning) return
            captureAndScan()
            mainHandler.postDelayed(this, SCAN_INTERVAL_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        textToSpeech = TextToSpeech(this, this)
        loadHistory()
        setContentView(buildUi())

        if (hasCameraPermission()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                CAMERA_PERMISSION_REQUEST
            )
        }
    }

    override fun onInit(status: Int) {
        isTtsReady = status == TextToSpeech.SUCCESS
        if (isTtsReady) {
            lmsAudioManager.configureDefaults()
        }
    }

    private fun buildUi(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(ScioColors.BACKGROUND)
        }
        root.addView(buildHeader())

        contentHost = FrameLayout(this)
        scannerScreen = buildScannerScreen()
        historyScreen = buildHistoryScreen()
        learnScreen = buildLearnScreen()
        aboutScreen = buildAboutScreen()
        contentHost.addView(scannerScreen)
        contentHost.addView(historyScreen)
        contentHost.addView(learnScreen)
        contentHost.addView(aboutScreen)
        root.addView(contentHost, LinearLayout.LayoutParams(-1, 0, 1f))

        root.addView(buildBottomNav())
        showTab(AppTab.SCANNER)
        return root
    }

    private fun buildHeader(): View {
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(8), dp(16), dp(8))
            setBackgroundColor(ScioColors.BACKGROUND)
        }
        header.addView(ImageView(this).apply {
            setImageResource(R.drawable.ic_launcher)
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
            setPadding(dp(5), dp(5), dp(5), dp(5))
        }, LinearLayout.LayoutParams(dp(48), dp(48)))
        header.addView(TextView(this).apply {
            text = BuildConfig.APP_TITLE_LABEL
            setTextColor(ScioColors.PRIMARY_CONTAINER)
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            includeFontPadding = false
            setPadding(dp(12), 0, 0, 0)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(TextView(this).apply {
            text = "Settings"
            setTextColor(ScioColors.MUTED)
            textSize = 12f
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(dp(74), dp(44)))
        return header
    }

    private fun buildScannerScreen(): View {
        val scroll = ScrollView(this).apply {
            isFillViewport = false
            setBackgroundColor(ScioColors.BACKGROUND)
        }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(16))
        }
        scroll.addView(body)

        val chips = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        chips.addView(chip("Language: English"), LinearLayout.LayoutParams(0, dp(52), 1f))
        chips.addView(SpaceView(this), LinearLayout.LayoutParams(dp(16), 1))
        chips.addView(chip("Grade 1"), LinearLayout.LayoutParams(0, dp(52), 1f))
        body.addView(chips)

        val previewHeight = (resources.displayMetrics.heightPixels * 0.46f).roundToInt()
            .coerceIn(dp(360), dp(560))
        val previewFrame = FrameLayout(this).apply {
            background = rounded(ScioColors.DARK, ScioColors.SECONDARY, 1, 12)
            clipToPadding = false
            setPadding(dp(1), dp(1), dp(1), dp(1))
        }
        previewView = PreviewView(this).apply {
            scaleType = PreviewView.ScaleType.FILL_CENTER
            setBackgroundColor(Color.BLACK)
        }
        detectionOverlay = DetectionOverlayView(this)
        frameOverlay = ScanFrameOverlayView(this)
        progress = ProgressBar(this).apply {
            isIndeterminate = true
            visibility = View.GONE
        }
        previewFrame.addView(previewView, FrameLayout.LayoutParams(-1, -1))
        previewFrame.addView(detectionOverlay, FrameLayout.LayoutParams(-1, -1))
        previewFrame.addView(frameOverlay, FrameLayout.LayoutParams(-1, -1))
        previewFrame.addView(progress, FrameLayout.LayoutParams(dp(56), dp(56), Gravity.CENTER))
        body.addView(previewFrame, LinearLayout.LayoutParams(-1, previewHeight).apply {
            topMargin = dp(20)
        })

        statsText = TextView(this).apply {
            text = "0 cells / 0% confidence / Ready"
            setTextColor(ScioColors.MUTED)
            textSize = 14f
            typeface = Typeface.MONOSPACE
            gravity = Gravity.CENTER
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 6)
            setPadding(dp(12), 0, dp(12), 0)
        }
        body.addView(statsText, LinearLayout.LayoutParams(-1, dp(48)).apply {
            topMargin = dp(16)
        })

        val controls = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(20), 0, dp(20))
        }
        flashButton = roundControl("Flash").apply { setOnClickListener { toggleTorch() } }
        scanButton = Button(this).apply {
            text = "Scan"
            isAllCaps = false
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(ScioColors.PRIMARY_CONTAINER, ScioColors.PRIMARY_FIXED, 4, 18)
            setOnClickListener {
                if (isScanning) stopScanning("Stopped") else startScanning()
            }
        }
        val languageButton = roundControl("Lang").apply {
            setOnClickListener { toast("English output is active") }
        }
        controls.addView(flashButton, LinearLayout.LayoutParams(dp(64), dp(64)))
        controls.addView(scanButton, LinearLayout.LayoutParams(dp(92), dp(92)).apply {
            leftMargin = dp(32)
            rightMargin = dp(32)
        })
        controls.addView(languageButton, LinearLayout.LayoutParams(dp(64), dp(64)))
        body.addView(controls)

        val resultCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(ScioColors.SECONDARY_CONTAINER, ScioColors.SECONDARY, 1, 12)
            setPadding(dp(20), dp(18), dp(20), dp(18))
        }
        braillePreviewText = TextView(this).apply {
            text = ""
            textSize = 24f
            letterSpacing = 0.08f
            setTextColor(ScioColors.SECONDARY)
            includeFontPadding = false
        }
        outputText = TextView(this).apply {
            text = "Tap Scan and point the camera at Braille."
            textSize = 32f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.SECONDARY)
            setPadding(0, dp(8), 0, dp(16))
        }
        resultCard.addView(braillePreviewText)
        resultCard.addView(outputText)

        val resultActions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        resultActions.addView(actionButton("Speak", true) { speakOutput() }, LinearLayout.LayoutParams(0, dp(56), 1f))
        resultActions.addView(SpaceView(this), LinearLayout.LayoutParams(dp(12), 1))
        resultActions.addView(actionButton("Copy", false) { copyOutput() }, LinearLayout.LayoutParams(0, dp(56), 1f))
        resultActions.addView(SpaceView(this), LinearLayout.LayoutParams(dp(12), 1))
        resultActions.addView(actionButton("Share", false) { shareOutput() }, LinearLayout.LayoutParams(0, dp(56), 1f))
        resultCard.addView(resultActions)
        body.addView(resultCard, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(18)
        })
        return scroll
    }

    private fun buildHistoryScreen(): View {
        val scroll = ScrollView(this).apply { setBackgroundColor(ScioColors.BACKGROUND) }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(22), dp(16), dp(24))
        }
        scroll.addView(body)
        body.addView(title("History"))
        val search = EditText(this).apply {
            hint = "Search transcripts..."
            textSize = 16f
            setSingleLine(true)
            setTextColor(ScioColors.TEXT)
            setHintTextColor(ScioColors.MUTED)
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 6)
            setPadding(dp(16), 0, dp(16), 0)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                    rebuildHistory(s?.toString().orEmpty())
                }
                override fun afterTextChanged(s: Editable?) = Unit
            })
        }
        body.addView(search, LinearLayout.LayoutParams(-1, dp(56)).apply {
            topMargin = dp(22)
            bottomMargin = dp(18)
        })
        val filters = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        filters.addView(filterChip("All", true))
        filters.addView(filterChip("Today", false))
        filters.addView(filterChip("This Week", false))
        body.addView(filters)
        historyList = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(18), 0, 0)
        }
        body.addView(historyList)
        rebuildHistory("")
        return scroll
    }

    private fun buildLearnScreen(): View {
        val scroll = ScrollView(this).apply { setBackgroundColor(ScioColors.BACKGROUND) }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(16), dp(32), dp(16), dp(28))
        }
        scroll.addView(body)
        learnTitleText = TextView(this).apply {
            text = "Learn Braille"
            textSize = 34f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            gravity = Gravity.CENTER
            includeFontPadding = false
        }
        body.addView(learnTitleText, LinearLayout.LayoutParams(-1, -2))
        learnSubtitleText = TextView(this).apply {
            text = "Audio-first Braille lessons with scanner practice"
            textSize = 17f
            setTextColor(ScioColors.MUTED)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.35f)
            setPadding(dp(12), dp(16), dp(12), dp(28))
        }
        body.addView(learnSubtitleText, LinearLayout.LayoutParams(-1, -2))
        learnLanguageButton = actionButton("Learning language: ${selectedLearningLanguage().displayName}", false) {
            showLearningLanguagePicker()
        }.apply {
            contentDescription = "Learning language: ${selectedLearningLanguage().displayName}. Choose a language curriculum."
        }
        body.addView(learnLanguageButton, LinearLayout.LayoutParams(-1, dp(52)).apply {
            bottomMargin = dp(8)
        })
        learnStatusText = TextView(this).apply {
            text = "Preparing lessons..."
            textSize = 14f
            typeface = Typeface.MONOSPACE
            setTextColor(ScioColors.MUTED)
            gravity = Gravity.CENTER
            setPadding(0, dp(22), 0, dp(10))
        }
        body.addView(learnStatusText, LinearLayout.LayoutParams(-1, -2))
        learnList = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(10), 0, 0)
        }
        body.addView(learnList, LinearLayout.LayoutParams(-1, -2))
        return scroll
    }

    private fun buildAboutScreen(): View {
        val scroll = ScrollView(this).apply { setBackgroundColor(ScioColors.BACKGROUND) }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(16), dp(24), dp(16), dp(28))
        }
        scroll.addView(body)
        body.addView(ImageView(this).apply {
            setImageResource(R.drawable.ic_launcher)
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 12)
            setPadding(dp(16), dp(16), dp(16), dp(16))
        }, LinearLayout.LayoutParams(dp(112), dp(112)))
        body.addView(TextView(this).apply {
            text = "SCIOBRAILLE"
            textSize = 34f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            gravity = Gravity.CENTER
            setPadding(0, dp(24), 0, dp(4))
        })
        body.addView(TextView(this).apply {
            text = "v1.2.0"
            textSize = 12f
            typeface = Typeface.MONOSPACE
            setTextColor(ScioColors.MUTED)
            gravity = Gravity.CENTER
            background = rounded(ScioColors.SURFACE_CONTAINER, ScioColors.OUTLINE, 1, 12)
            setPadding(dp(12), dp(4), dp(12), dp(4))
        })
        body.addView(TextView(this).apply {
            text = "Bringing vision to touch. Real-time Braille OCR designed for fast reading assistance."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.35f)
            setPadding(dp(16), dp(22), dp(16), dp(22))
        })
        val statRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        statRow.addView(statCard(historyEntries.size.toString(), "Scans"), LinearLayout.LayoutParams(0, dp(112), 1f))
        statRow.addView(SpaceView(this), LinearLayout.LayoutParams(dp(12), 1))
        statRow.addView(statCard("1", "Language"), LinearLayout.LayoutParams(0, dp(112), 1f))
        statRow.addView(SpaceView(this), LinearLayout.LayoutParams(dp(12), 1))
        statRow.addView(statCard("93%", "Accuracy"), LinearLayout.LayoutParams(0, dp(112), 1f))
        body.addView(statRow, LinearLayout.LayoutParams(-1, -2))
        body.addView(infoCard("How it works", listOf(
            "1  Point your phone camera at physical Braille.",
            "2  Live detection highlights each Braille cell.",
            "3  Read, copy, share, or listen to the English output."
        )), LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(28) })
        body.addView(infoCard("Key features", listOf(
            "Real-time scanner",
            "Bounding box guidance",
            "Audio output",
            "Backend plus offline fallback"
        )), LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(20) })
        return scroll
    }

    private fun buildBottomNav(): View {
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(dp(14), dp(8), dp(14), dp(8))
            background = rounded(ScioColors.BACKGROUND, ScioColors.OUTLINE, 1, 0)
        }
        scannerNav = navItem("Scanner", "Scanner tab") { showTab(AppTab.SCANNER) }
        historyNav = navItem("History", "History tab") { showTab(AppTab.HISTORY) }
        learnNav = navItem("Learn", "Learn Braille tab") { showTab(AppTab.LEARN) }
        aboutNav = navItem("About", "About BrailleEye tab") { showTab(AppTab.ABOUT) }
        nav.addView(scannerNav, LinearLayout.LayoutParams(0, dp(64), 1f))
        nav.addView(historyNav, LinearLayout.LayoutParams(0, dp(64), 1f))
        nav.addView(learnNav, LinearLayout.LayoutParams(0, dp(64), 1f))
        nav.addView(aboutNav, LinearLayout.LayoutParams(0, dp(64), 1f))
        return nav
    }

    private fun showTab(tab: AppTab) {
        currentTab = tab
        scannerScreen.visibility = if (tab == AppTab.SCANNER) View.VISIBLE else View.GONE
        historyScreen.visibility = if (tab == AppTab.HISTORY) View.VISIBLE else View.GONE
        learnScreen.visibility = if (tab == AppTab.LEARN) View.VISIBLE else View.GONE
        aboutScreen.visibility = if (tab == AppTab.ABOUT) View.VISIBLE else View.GONE
        if (tab != AppTab.SCANNER && isScanning) stopScanning("Stopped")
        updateNav()
        if (tab == AppTab.HISTORY) rebuildHistory("")
        if (tab == AppTab.LEARN) loadLearnLessons()
    }

    private fun updateNav() {
        updateNavItem(scannerNav, currentTab == AppTab.SCANNER)
        updateNavItem(historyNav, currentTab == AppTab.HISTORY)
        updateNavItem(learnNav, currentTab == AppTab.LEARN)
        updateNavItem(aboutNav, currentTab == AppTab.ABOUT)
    }

    private fun updateNavItem(view: TextView, selected: Boolean) {
        view.setTextColor(if (selected) ScioColors.TEXT else ScioColors.MUTED)
        view.typeface = if (selected) Typeface.DEFAULT_BOLD else Typeface.MONOSPACE
        view.background = if (selected) {
            rounded(if (view == historyNav || view == aboutNav) ScioColors.SECONDARY_CONTAINER else ScioColors.PRIMARY_CONTAINER, null, 0, 16)
        } else {
            rounded(Color.TRANSPARENT, null, 0, 16)
        }
    }

    private fun loadLearnLessons() {
        if (!::learnList.isInitialized || !::learnStatusText.isInitialized) return
        if (::learnTitleText.isInitialized) learnTitleText.visibility = View.VISIBLE
        if (::learnSubtitleText.isInitialized) learnSubtitleText.visibility = View.VISIBLE
        if (::learnLanguageButton.isInitialized) {
            learnLanguageButton.visibility = View.VISIBLE
            updateLearningLanguageButton()
        }
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Loading curriculum..."
        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    lmsRepository.seedDefaultCurriculumIfNeeded()
                    syncManager.syncAll()
                    val lessons = lmsRepository.getAllLessons()
                    val progress = lmsRepository.getAllProgress()
                    lessons to progress
                }
            }.onSuccess { (lessons, progress) ->
                renderLearnHome(lessons, progress)
            }.onFailure { error ->
                learnStatusText.text = "Could not load lessons"
                learnList.removeAllViews()
                learnList.addView(TextView(this@MainActivity).apply {
                    text = error.message ?: "Unknown LMS error"
                    textSize = 15f
                    setTextColor(ScioColors.ERROR)
                    background = rounded(ScioColors.SURFACE, ScioColors.ERROR, 1, 8)
                    setPadding(dp(16), dp(14), dp(16), dp(14))
                }, LinearLayout.LayoutParams(-1, -2))
            }
        }
    }

    private fun renderLearnHome(
        lessons: List<LessonEntity>,
        progress: List<LessonProgressEntity>
    ) {
        learnList.removeAllViews()
        val language = selectedLearningLanguage()
        val languageLessons = lessons.filter { it.languageCode == language.code }
        if (language != Language.ENGLISH) {
            learnStatusText.text = "${language.displayName} curriculum"
            learnList.addView(infoCard(language.displayName, listOf(
                "This language curriculum is coming soon.",
                "Verified Braille mappings are required before lessons can be enabled."
            )).apply {
                contentDescription = "${language.displayName} curriculum. This language curriculum is coming soon."
            }, LinearLayout.LayoutParams(-1, -2))
            return
        }
        val states = buildLevelStates(languageLessons, progress)
        learnStatusText.text = "${states.count { it.unlocked }} of 6 levels unlocked"
        learnList.addView(actionButton("My Progress", true) { renderLmsProgress() }.apply {
            contentDescription = "My Progress. Open your learning progress, streaks, letter accuracy, and recent lessons."
        }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(18)
        })
        learnList.addView(actionButton("Milestones and Certificates", false) { renderMilestoneList() }.apply {
            contentDescription = "Milestones and Certificates. View earned learning milestones and certificates."
        }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(18)
        })
        states.forEach { state ->
            learnList.addView(levelCard(state), LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(14)
            })
        }
    }

    private fun renderLmsProgress() {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Loading your progress..."
        learnList.removeAllViews()
        lifecycleScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    lmsRepository.seedDefaultCurriculumIfNeeded()
                    LmsProgressSnapshot(
                        lessons = lmsRepository.getLessonsByLanguage(Language.ENGLISH),
                        progress = lmsRepository.getAllProgress(),
                        letterAccuracies = lmsRepository.getAllLetterAccuracies(),
                        streak = lmsRepository.getStreak(),
                        syncOverview = lmsRepository.getSyncOverview()
                    )
                }
            }.onSuccess { snapshot ->
                renderLmsProgressContent(snapshot)
            }.onFailure { error ->
                learnStatusText.text = "Could not load progress"
                learnList.addView(TextView(this@MainActivity).apply {
                    text = error.message ?: "Unknown LMS error"
                    setTextColor(ScioColors.ERROR)
                    setPadding(dp(16), dp(16), dp(16), dp(16))
                })
            }
        }
    }

    private fun renderLmsProgressContent(snapshot: LmsProgressSnapshot) {
        learnList.removeAllViews()
        learnStatusText.text = "Your learning progress"
        learnList.addView(actionButton("Back to Learn", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(52)).apply {
            bottomMargin = dp(16)
        })

        val completed = snapshot.progress.count { it.status == LessonProgressStatus.COMPLETED }
        val total = snapshot.lessons.size
        val overallPercent = if (total == 0) 0 else (completed * 100f / total).roundToInt()
        learnList.addView(progressSummaryCard(
            title = "Overall progress",
            summary = "$overallPercent% complete. $completed of $total lessons complete.",
            progressPercent = overallPercent,
            contentDescription = "Overall LMS progress: $overallPercent percent complete. $completed of $total lessons complete."
        ), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })

        val syncText = syncStatusText(snapshot.syncOverview)
        learnList.addView(infoCard("Sync status", listOf(syncText)).apply {
            contentDescription = "Sync status. $syncText"
        }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        learnList.addView(actionButton("Sync now", true) {
            learnStatusText.text = "Syncing progress..."
            lifecycleScope.launch {
                val result = withContext(Dispatchers.IO) { syncManager.syncAll() }
                toast(result.message)
                renderLmsProgress()
            }
        }.apply {
            isEnabled = snapshot.syncOverview.status != SyncStatus.SYNCING
            contentDescription = "Sync now. $syncText"
        }, LinearLayout.LayoutParams(-1, dp(52)).apply { bottomMargin = dp(14) })

        val currentStreak = snapshot.streak?.currentStreak ?: 0
        val longestStreak = snapshot.streak?.longestStreak ?: 0
        learnList.addView(infoCard("Learning streak", listOf(
            "Current streak: $currentStreak day${if (currentStreak == 1) "" else "s"}.",
            "Longest streak: $longestStreak day${if (longestStreak == 1) "" else "s"}."
        )).apply {
            contentDescription = "Learning streak. Current streak: $currentStreak days. Longest streak: $longestStreak days."
        }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })

        val states = buildLevelStates(snapshot.lessons, snapshot.progress)
        learnList.addView(TextView(this).apply {
            text = "Level progress"
            textSize = 23f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(8), 0, dp(10))
        })
        states.forEach { state ->
            val summary = "Level ${state.level} ${state.title}: ${state.completedLessons} of ${state.totalLessons} lessons complete. ${state.progressPercent}% complete."
            learnList.addView(progressSummaryCard(
                title = "Level ${state.level} - ${state.title}",
                summary = summary,
                progressPercent = state.progressPercent,
                contentDescription = summary
            ), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
        }

        val weekStart = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(7)
        val completedThisWeek = snapshot.progress.count {
            it.status == LessonProgressStatus.COMPLETED && (it.completedAt ?: 0L) >= weekStart
        }
        val encouragement = if (completedThisWeek > 0) {
            "Great work. You completed $completedThisWeek lesson${if (completedThisWeek == 1) "" else "s"} this week."
        } else {
            "Start a short practice session today to build your learning streak."
        }
        val practicedLetters = snapshot.letterAccuracies.entries.sortedBy { it.value }
        val practiceSuggestion = if (practicedLetters.size >= 2) {
            "Practice letters ${practicedLetters[0].key} and ${practicedLetters[1].key} to improve recognition."
        } else {
            "Complete Letter Recognition practice to see suggestions for letters to revisit."
        }
        learnList.addView(infoCard("Next steps", listOf(encouragement, practiceSuggestion)), LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(8)
            bottomMargin = dp(14)
        })

        learnList.addView(TextView(this).apply {
            text = "Accuracy by letter"
            textSize = 23f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(8), 0, dp(10))
        })
        ('A'..'Z').forEach { letter ->
            val accuracy = snapshot.letterAccuracies[letter]
            val text = if (accuracy == null) {
                "$letter: no recognition answers recorded yet."
            } else {
                "$letter: ${accuracy.roundToInt()}% accuracy."
            }
            learnList.addView(TextView(this).apply {
                this.text = text
                textSize = 16f
                setTextColor(ScioColors.TEXT)
                background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
                setPadding(dp(16), dp(12), dp(16), dp(12))
                contentDescription = "Letter accuracy. $text"
            }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(7) })
        }

        learnList.addView(TextView(this).apply {
            text = "Recent completed lessons"
            textSize = 23f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(18), 0, dp(10))
        })
        val lessonTitles = snapshot.lessons.associate { it.id to it.title }
        val recent = snapshot.progress
            .filter { it.status == LessonProgressStatus.COMPLETED && it.completedAt != null }
            .sortedByDescending { it.completedAt }
            .take(5)
        if (recent.isEmpty()) {
            learnList.addView(TextView(this).apply {
                text = "No lessons completed yet. Your completed lessons will appear here."
                textSize = 16f
                setTextColor(ScioColors.MUTED)
                setPadding(dp(16), dp(14), dp(16), dp(14))
            })
        } else {
            recent.forEach { item ->
                val date = DateFormat.getDateInstance(DateFormat.MEDIUM, Locale.getDefault())
                    .format(Date(item.completedAt ?: item.updatedAt))
                val title = lessonTitles[item.lessonId] ?: item.lessonId
                val text = "$title completed on $date. Score ${item.score}. Accuracy ${item.accuracy.roundToInt()}%."
                learnList.addView(TextView(this).apply {
                    this.text = text
                    textSize = 16f
                    setTextColor(ScioColors.TEXT)
                    background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
                    setPadding(dp(16), dp(12), dp(16), dp(12))
                    contentDescription = "Recent completed lesson. $text"
                }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(8) })
            }
        }
    }

    private fun progressSummaryCard(
        title: String,
        summary: String,
        progressPercent: Int,
        contentDescription: String
    ): View = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
        setPadding(dp(18), dp(16), dp(18), dp(18))
        this.contentDescription = contentDescription
        addView(TextView(context).apply {
            text = title
            textSize = 19f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
        })
        addView(TextView(context).apply {
            text = summary
            textSize = 16f
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(10), 0, dp(8))
        })
        addView(progressBar(progressPercent).apply {
            this.contentDescription = "$title progress: $progressPercent percent."
        }, LinearLayout.LayoutParams(-1, dp(10)))
    }

    private fun syncStatusText(overview: SyncOverview): String = when (overview.status) {
        SyncStatus.SYNCED -> "Synced${overview.lastSyncedAt?.let { ". Last synced: ${formatSyncDateTime(it)}" }.orEmpty()}"
        SyncStatus.SYNCING -> "Syncing"
        SyncStatus.FAILED -> "Sync failed. Try again."
        SyncStatus.NOT_SYNCED -> if (entitlementManager.canUseCloudSync()) {
            "Not synced. Progress saved on this device. It will sync when internet is available."
        } else {
            "Not synced. Cloud sync is available with Premium."
        }
    }

    private fun formatSyncDateTime(timestamp: Long): String =
        DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT, Locale.getDefault()).format(Date(timestamp))

    private fun lmsSyncUserId(): String {
        val preferences = getSharedPreferences("sciobraille_lms_sync", MODE_PRIVATE)
        return preferences.getString("installation_user_id", null) ?: "device-${UUID.randomUUID()}".also { id ->
            preferences.edit().putString("installation_user_id", id).apply()
        }
    }

    private fun syncLmsAfterLessonCompletion() {
        lifecycleScope.launch {
            val awards = withContext(Dispatchers.IO) {
                val newAwards = milestoneManager.evaluateAndAward()
                syncManager.syncAll()
                newAwards
            }
            if (awards.isNotEmpty() && currentTab == AppTab.LEARN) {
                renderCertificateScreen(awards.first())
            }
        }
    }

    private fun renderMilestoneList() {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Milestones and Certificates"
        learnList.removeAllViews()
        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        val awards = milestoneManager.getAwards()
        if (awards.isEmpty()) {
            learnList.addView(infoCard("Keep learning", listOf(
                "Complete lessons to earn milestones and certificates.",
                "Your certificates will appear here after they are earned."
            )), LinearLayout.LayoutParams(-1, -2))
            return
        }
        awards.forEach { award ->
            val date = formatSyncDateTime(award.awardedAt)
            learnList.addView(actionButton("${award.milestone.title} - $date", false) {
                renderCertificateScreen(award)
            }.apply {
                contentDescription = "Certificate: ${award.milestone.title}, awarded $date"
            }, LinearLayout.LayoutParams(-1, dp(60)).apply { bottomMargin = dp(10) })
        }
    }

    private fun renderCertificateScreen(award: MilestoneAward) {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Certificate earned"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)
        val learner = milestoneManager.learnerName()
        val date = formatSyncDateTime(award.awardedAt)
        val certificateText = "BrailleEye LMS certificate. Presented to $learner for ${award.milestone.title}. Awarded $date."
        learnList.addView(actionButton("Back to Milestones", false) { renderMilestoneList() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.SECONDARY, 2, 8)
            setPadding(dp(22), dp(28), dp(22), dp(28))
            contentDescription = certificateText
            addView(TextView(context).apply {
                text = "BRAILLEEYE LMS"
                textSize = 17f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.SECONDARY)
            })
            addView(TextView(context).apply {
                text = "Certificate of Achievement"
                textSize = 28f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.TEXT)
                setPadding(0, dp(20), 0, dp(18))
            })
            addView(TextView(context).apply {
                text = "Presented to"
                textSize = 15f
                gravity = Gravity.CENTER
                setTextColor(ScioColors.MUTED)
            })
            addView(TextView(context).apply {
                text = learner
                textSize = 24f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.TEXT)
                setPadding(0, dp(6), 0, dp(18))
            })
            addView(TextView(context).apply {
                text = award.milestone.title
                textSize = 20f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.PRIMARY)
            })
            addView(TextView(context).apply {
                text = "Awarded $date"
                textSize = 15f
                gravity = Gravity.CENTER
                setTextColor(ScioColors.MUTED)
                setPadding(0, dp(20), 0, 0)
            })
        }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
        learnList.addView(actionButton("Share certificate", true) {
            startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, certificateText)
            }, "Share certificate"))
        }, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(10) })
        learnList.addView(actionButton("Download certificate", false) {
            toast("PDF download will be available when certificate PDF generation is added.")
        }, LinearLayout.LayoutParams(-1, dp(54)))
    }

    private fun renderUpgradeScreen(feature: String) {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Premium learning"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)
        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(TextView(this).apply {
            text = "Unlock full Braille learning"
            textSize = 28f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(12))
        })
        learnList.addView(TextView(this).apply {
            text = "$feature is part of Premium."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            setPadding(0, 0, 0, dp(14))
        })
        learnList.addView(infoCard("Premium includes", listOf(
            "Complete A-Z Braille lessons",
            "Practice real Braille with scanner-based learning",
            "Track progress and accuracy",
            "Learn Grade 2 contractions",
            "Sync progress across devices"
        )), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
        learnList.addView(actionButton("Upgrade", true) {
            toast("Payments are not configured yet.")
        }, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(10) })
        learnList.addView(actionButton("Use school code", false) {
            val input = EditText(this).apply {
                hint = "School code"
                contentDescription = "School code"
            }
            AlertDialog.Builder(this)
                .setTitle("Use school code")
                .setView(input)
                .setPositiveButton("Submit") { _, _ ->
                    entitlementManager.savePendingSchoolCode(input.text.toString())
                    toast("School code saved for verification. Access changes after school verification.")
                }
                .setNegativeButton("Cancel", null)
                .show()
        }, LinearLayout.LayoutParams(-1, dp(54)))
    }

    private fun selectedLearningLanguage(): Language {
        val preferences = getSharedPreferences("sciobraille_lms_settings", MODE_PRIVATE)
        return Language.fromCode(preferences.getString("learning_language", Language.ENGLISH.code))
    }

    private fun showLearningLanguagePicker() {
        val languages = Language.entries.toList()
        val selectedIndex = languages.indexOf(selectedLearningLanguage()).coerceAtLeast(0)
        AlertDialog.Builder(this)
            .setTitle("Learning language")
            .setSingleChoiceItems(languages.map { it.displayName }.toTypedArray(), selectedIndex) { dialog, which ->
                val language = languages[which]
                getSharedPreferences("sciobraille_lms_settings", MODE_PRIVATE)
                    .edit()
                    .putString("learning_language", language.code)
                    .apply()
                updateLearningLanguageButton()
                dialog.dismiss()
                loadLearnLessons()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun updateLearningLanguageButton() {
        if (!::learnLanguageButton.isInitialized) return
        val language = selectedLearningLanguage()
        learnLanguageButton.text = "Learning language: ${language.displayName}"
        learnLanguageButton.contentDescription = "Learning language: ${language.displayName}. Choose a language curriculum."
    }

    private fun buildLevelStates(
        lessons: List<LessonEntity>,
        progress: List<LessonProgressEntity>
    ): List<LmsLevelState> {
        val lessonsByLevel = lessons.groupBy { it.level }
        val progressByLessonId = progress.associateBy { it.lessonId }
        val completedByLevel = lessonsByLevel.mapValues { (_, levelLessons) ->
            levelLessons.count { lesson ->
                progressByLessonId[lesson.id]?.status == LessonProgressStatus.COMPLETED
            }
        }
        val totalByLevel = lessonsByLevel.mapValues { it.value.size }
        val level3Accuracy = LmsProgressRules.averageCompletedAccuracy(progress, 3)
        val level4Accuracy = LmsProgressRules.averageCompletedAccuracy(progress, 4)

        fun levelCompleted(level: Int): Boolean {
            val total = totalByLevel[level] ?: 0
            return LmsProgressRules.isLevelComplete(
                completedByLevel[level] ?: 0,
                total,
                if (level == 4) 70f else null,
                level4Accuracy
            )
        }

        fun state(
            level: Int,
            title: String,
            description: String,
            cta: String,
            unlocked: Boolean,
            lockedReason: String
        ): LmsLevelState {
            val total = totalByLevel[level] ?: 0
            val completed = completedByLevel[level] ?: 0
            val progressPercent = LmsProgressRules.completionPercent(completed, total)
            return LmsLevelState(
                level = level,
                title = title,
                description = description,
                cta = cta,
                progressPercent = progressPercent,
                completedLessons = completed,
                totalLessons = total,
                unlocked = unlocked,
                lockedReason = if (unlocked) "" else lockedReason,
                lessons = lessonsByLevel[level].orEmpty().sortedBy { it.orderIndex }
            )
        }

        val premium = entitlementManager.hasFullLearningAccess()
        val freeLettersCompleted = (completedByLevel[2] ?: 0) >= 5
        return listOf(
            state(
                level = 1,
                title = "Dot Explorer",
                description = "Learn the six Braille dot positions.",
                cta = "Start",
                unlocked = true,
                lockedReason = ""
            ),
            state(
                level = 2,
                title = "Letter Builder",
                description = "Build letters from dots.",
                cta = "Continue",
                unlocked = LmsProgressRules.canUnlockLetterBuilder(levelCompleted(1)),
                lockedReason = "Complete Level 1 to unlock Letter Builder."
            ),
            state(
                level = 3,
                title = "Letter Recognition",
                description = "Recognize Braille letters by touch, sound, and position.",
                cta = "Practice",
                unlocked = LmsProgressRules.canUnlockRecognition(premium, completedByLevel[2] ?: 0, entitlementManager.canAccessLevel(3)),
                lockedReason = if (!premium && !freeLettersCompleted) {
                    "Complete free letters A through E to unlock one recognition practice session."
                } else if (!premium) {
                    entitlementManager.lockedReason("More Letter Recognition practice")
                } else {
                    "Complete at least 10 Level 2 letter lessons to unlock recognition practice."
                }
            ),
            state(
                level = 4,
                title = "Word Reading",
                description = "Read simple Braille words cell by cell.",
                cta = "Read",
                unlocked = LmsProgressRules.canUnlockPremiumLevel(premium, level3Accuracy >= 70f),
                lockedReason = if (premium) "Reach 70% average accuracy in Level 3 to unlock word reading." else entitlementManager.lockedReason("Word Reading")
            ),
            state(
                level = 5,
                title = "Grade 2 Contractions",
                description = "Learn common contractions used in real Braille books.",
                cta = "Learn",
                unlocked = LmsProgressRules.canUnlockPremiumLevel(premium, levelCompleted(4)),
                lockedReason = if (premium) "Complete Level 4 to unlock Grade 2 contractions." else entitlementManager.lockedReason("Grade 2 Contractions")
            ),
            state(
                level = 6,
                title = "Scan and Learn",
                description = "Scan real Braille and learn from detected cells.",
                cta = "Scan Practice",
                unlocked = LmsProgressRules.canUnlockPremiumLevel(premium, levelCompleted(1)),
                lockedReason = if (premium) "Complete Level 1 to unlock scanner practice." else entitlementManager.lockedReason("Scan and Learn explanations")
            )
        )
    }

    private fun levelCard(state: LmsLevelState): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(18), dp(16), dp(18), dp(18))
            contentDescription = levelContentDescription(state)
            addView(TextView(context).apply {
                text = "Level ${state.level} - ${state.title}"
                textSize = 20f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(ScioColors.TEXT)
            })
            addView(TextView(context).apply {
                text = state.description
                textSize = 15f
                setTextColor(ScioColors.MUTED)
                setLineSpacing(0f, 1.28f)
                setPadding(0, dp(8), 0, 0)
            })
            addView(TextView(context).apply {
                text = "Progress: ${state.progressPercent}%"
                textSize = 14f
                typeface = Typeface.MONOSPACE
                setTextColor(ScioColors.TEXT)
                setPadding(0, dp(12), 0, 0)
            })
            addView(progressBar(state.progressPercent), LinearLayout.LayoutParams(-1, dp(10)).apply {
                topMargin = dp(8)
            })
            addView(TextView(context).apply {
                text = "Completed: ${state.completedLessons}/${state.totalLessons} lessons"
                textSize = 14f
                setTextColor(ScioColors.TEXT)
                setPadding(0, dp(10), 0, 0)
            })
            addView(TextView(context).apply {
                text = if (state.unlocked) "Status: Unlocked" else "Status: Locked - ${state.lockedReason}"
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(if (state.unlocked) ScioColors.PRIMARY else ScioColors.ERROR)
                setPadding(0, dp(8), 0, dp(12))
            })
            addView(actionButton(state.cta, state.unlocked) {
                if (state.unlocked) {
                    renderLevelPlaceholder(state)
                } else {
                    renderUpgradeScreen(state.title)
                }
            }.apply {
                isEnabled = true
                contentDescription = if (state.unlocked) {
                    "${state.cta}, open Level ${state.level} ${state.title}"
                } else {
                    "Locked Level ${state.level} ${state.title}. ${state.lockedReason}"
                }
            }, LinearLayout.LayoutParams(-1, dp(54)))
        }
    }

    private fun progressBar(progressPercent: Int): View {
        return LevelProgressView(this, progressPercent)
    }

    private fun renderLevelPlaceholder(state: LmsLevelState) {
        if (!entitlementManager.canAccessLevel(state.level)) {
            renderUpgradeScreen(state.title)
            return
        }
        if (state.level == 1) {
            renderDotExplorer(state)
            return
        }
        if (state.level == 2) {
            renderLetterBuilderList(state)
            return
        }
        if (state.level == 3) {
            renderLetterRecognition(state)
            return
        }
        if (state.level == 4) {
            renderWordReading(state)
            return
        }
        if (state.level == 5) {
            renderGrade2ContractionsList(state)
            return
        }
        if (state.level == 6) {
            renderScanAndLearnIntro(state)
            return
        }
        learnList.removeAllViews()
        learnStatusText.text = "Level ${state.level} opened"
        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(TextView(this).apply {
            text = "Level ${state.level} - ${state.title}"
            textSize = 24f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(8))
        }, LinearLayout.LayoutParams(-1, -2))
        learnList.addView(TextView(this).apply {
            text = "Lesson screen placeholder. ${state.lessons.size} lessons are available in this level."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            setLineSpacing(0f, 1.35f)
            setPadding(0, 0, 0, dp(12))
        }, LinearLayout.LayoutParams(-1, -2))
        state.lessons.forEach { lesson ->
            learnList.addView(TextView(this).apply {
                text = "${lesson.orderIndex}. ${lesson.title}\n${lesson.description}"
                textSize = 15f
                setTextColor(ScioColors.TEXT)
                background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
                setPadding(dp(14), dp(12), dp(14), dp(12))
            }, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun renderLetterBuilderList(state: LmsLevelState) {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Letter Builder"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(TextView(this).apply {
            text = "Level 2 - Letter Builder"
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(8))
        })
        learnList.addView(TextView(this).apply {
            text = "Build each English Braille letter from its dot pattern."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            setLineSpacing(0f, 1.35f)
            setPadding(0, 0, 0, dp(14))
        })

        lifecycleScope.launch {
            val progress = withContext(Dispatchers.IO) { lmsRepository.getAllProgress() }
            val progressByLessonId = progress.associateBy { it.lessonId }
            state.lessons.sortedBy { it.orderIndex }.forEach { lesson ->
                val letter = lesson.id.substringAfterLast("-").uppercase(Locale.US).firstOrNull() ?: return@forEach
                val status = progressByLessonId[lesson.id]?.status ?: LessonProgressStatus.NOT_STARTED
                learnList.addView(letterLessonCard(letter, lesson, status), LinearLayout.LayoutParams(-1, -2).apply {
                    bottomMargin = dp(10)
                })
            }
        }
    }

    private fun letterLessonCard(letter: Char, lesson: LessonEntity, status: String): View {
        val dots = BrailleMappings.getDotsForLetter(letter)
        val hasAccess = entitlementManager.canAccessLetter(letter)
        val statusText = when (status) {
            LessonProgressStatus.COMPLETED -> "Completed"
            LessonProgressStatus.IN_PROGRESS -> "In progress"
            else -> "Not started"
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(16), dp(14), dp(16), dp(14))
            contentDescription = if (hasAccess) {
                "Letter $letter lesson, $statusText, dots ${formatDots(dots)}"
            } else {
                "Letter $letter lesson locked. ${entitlementManager.lockedReason("Letter $letter")}" 
            }
            setOnClickListener {
                if (hasAccess) renderLetterBuilderLesson(letter, lesson) else renderUpgradeScreen("Letter $letter")
            }
            addView(TextView(context).apply {
                text = letter.toString()
                textSize = 30f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.TEXT)
                background = rounded(ScioColors.SURFACE_CONTAINER, ScioColors.OUTLINE, 1, 12)
            }, LinearLayout.LayoutParams(dp(58), dp(58)))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(14), 0, 0, 0)
                addView(TextView(context).apply {
                    text = "Letter $letter"
                    textSize = 18f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(ScioColors.TEXT)
                })
                addView(TextView(context).apply {
                    text = if (hasAccess) "Dots ${formatDots(dots)} - $statusText" else "Premium lesson"
                    textSize = 14f
                    setTextColor(ScioColors.MUTED)
                    setPadding(0, dp(4), 0, 0)
                })
            }, LinearLayout.LayoutParams(0, -2, 1f))
            addView(TextView(context).apply {
                text = if (hasAccess) "Open" else "Locked"
                textSize = 13f
                typeface = Typeface.MONOSPACE
                setTextColor(ScioColors.SECONDARY)
                gravity = Gravity.CENTER
            }, LinearLayout.LayoutParams(dp(54), dp(48)))
        }
    }

    private fun renderLetterBuilderLesson(letter: Char, lesson: LessonEntity) {
        if (!entitlementManager.canAccessLetter(letter)) {
            renderUpgradeScreen("Letter $letter")
            return
        }
        val requiredDots = BrailleMappings.getDotsForLetter(letter)
        val confirmedDots = linkedSetOf<Int>()
        var lastInstruction = "${letterInstruction(letter, requiredDots)} Tap ${tapPrompt(requiredDots)} to confirm."

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.GONE
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(18))
            background = rounded(0xFF111217.toInt(), null, 0, 14)
        }
        learnList.addView(root, LinearLayout.LayoutParams(-1, -2))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(Button(this).apply {
            text = "Back"
            isAllCaps = false
            textSize = 13f
            setTextColor(Color.WHITE)
            contentDescription = "Back to Letter Builder lessons"
            background = rounded(0xFF2D3040.toInt(), 0xFF868BE8.toInt(), 1, 10)
            setOnClickListener {
                lifecycleScope.launch {
                    val lessons = withContext(Dispatchers.IO) {
                        lmsRepository.seedDefaultCurriculumIfNeeded()
                        lmsRepository.getLessonsByLevel(2)
                    }
                    renderLetterBuilderList(
                        LmsLevelState(
                            level = 2,
                            title = "Letter Builder",
                            description = "Build letters from dots.",
                            cta = "Continue",
                            progressPercent = 0,
                            completedLessons = 0,
                            totalLessons = lessons.size,
                            unlocked = true,
                            lockedReason = "",
                            lessons = lessons
                        )
                    )
                }
            }
        }, LinearLayout.LayoutParams(dp(74), dp(48)))
        header.addView(TextView(this).apply {
            text = "Letter $letter"
            textSize = 24f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, dp(8), 0)
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        root.addView(header)

        val instructionText = TextView(this).apply {
            text = letterInstruction(letter, requiredDots)
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(0xFFECEAF6.toInt())
            setLineSpacing(0f, 1.3f)
            setPadding(0, dp(18), 0, dp(14))
            contentDescription = text
        }
        root.addView(instructionText)

        val cellView = BrailleCellView(this).apply {
            activeDots = requiredDots
            visitedDots = confirmedDots
            showDotNumbers = true
            interactive = true
        }
        root.addView(cellView, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(8)
            bottomMargin = dp(18)
        })

        val statusText = TextView(this).apply {
            text = "Confirm dots: 0/${requiredDots.size}"
            textSize = 16f
            typeface = Typeface.MONOSPACE
            setTextColor(0xFFE6E1FF.toInt())
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(12))
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        root.addView(statusText)

        val controls = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        root.addView(controls)

        lateinit var nextButton: Button
        lateinit var refreshUi: () -> Unit

        cellView.onDotClick = { dot ->
            if (dot in requiredDots) {
                confirmedDots.add(dot)
                lmsHapticManager.success()
                if (confirmedDots.containsAll(requiredDots)) {
                    lastInstruction = "Correct. This is the letter $letter."
                    lmsAudioManager.speakCorrect(lastInstruction)
                } else {
                    lastInstruction = "Correct. Dot $dot is part of letter $letter."
                    lmsAudioManager.speakCorrect(lastInstruction)
                }
            } else {
                lmsHapticManager.error()
                lastInstruction = "Try again. ${letterInstruction(letter, requiredDots)}"
                lmsAudioManager.speakIncorrect(lastInstruction)
            }
            refreshUi()
        }

        controls.addView(actionButton("Repeat", false) {
            lmsAudioManager.repeatLast()
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        controls.addView(actionButton("Reset", false) {
            confirmedDots.clear()
            lastInstruction = "${letterInstruction(letter, requiredDots)} Tap ${tapPrompt(requiredDots)} to confirm."
            refreshUi()
            lmsAudioManager.speakLetter(letter, requiredDots)
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        nextButton = actionButton("Next Letter", true) {
            if (!confirmedDots.containsAll(requiredDots)) {
                toast("Confirm all correct dots first")
                return@actionButton
            }
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.markLessonCompleted(
                        lessonId = lesson.id,
                        level = 2,
                        score = 100,
                        accuracy = 100f
                    )
                }
                syncLmsAfterLessonCompletion()
                val nextLesson = withContext(Dispatchers.IO) {
                    lmsRepository.getLessonsByLevel(2)
                        .sortedBy { it.orderIndex }
                        .firstOrNull { it.orderIndex > lesson.orderIndex }
                }
                if (nextLesson != null) {
                    val nextLetter = nextLesson.id.substringAfterLast("-").uppercase(Locale.US).first()
                    renderLetterBuilderLesson(nextLetter, nextLesson)
                } else {
                    lmsHapticManager.completion()
                    lmsAudioManager.speakCorrect("Letter Builder complete.")
                    loadLearnLessons()
                }
            }
        }
        controls.addView(nextButton, LinearLayout.LayoutParams(0, dp(54), 1f))

        refreshUi = {
            val complete = confirmedDots.containsAll(requiredDots)
            cellView.visitedDots = confirmedDots
            statusText.text = "Confirm dots: ${confirmedDots.size}/${requiredDots.size}"
            nextButton.isEnabled = complete
            nextButton.alpha = if (complete) 1f else 0.45f
            nextButton.contentDescription = if (complete) {
                "Next Letter, save Letter $letter progress"
            } else {
                "Next Letter locked. Confirm ${requiredDots.size - confirmedDots.size} more correct dots."
            }
        }
        refreshUi()
        lmsAudioManager.speakLetter(letter, requiredDots)
        lifecycleScope.launch {
            withContext(Dispatchers.IO) { lmsRepository.markLessonStarted(lesson.id, 2) }
        }
    }

    private fun letterInstruction(letter: Char, dots: Set<Int>): String {
        return "Letter $letter uses ${dotPhrase(dots)}."
    }

    private fun dotPhrase(dots: Set<Int>): String {
        val sorted = dots.sorted()
        return when (sorted.size) {
            0 -> "no dots"
            1 -> "dot ${sorted.first()} only"
            2 -> "dots ${sorted[0]} and ${sorted[1]}"
            else -> "dots ${sorted.dropLast(1).joinToString(", ")}, and ${sorted.last()}"
        }
    }

    private fun tapPrompt(dots: Set<Int>): String {
        return if (dots.size == 1) "dot ${dots.first()}" else "the active dots ${formatDots(dots)}"
    }

    private fun formatDots(dots: Set<Int>): String {
        return dots.sorted().joinToString(", ")
    }

    private fun renderLetterRecognition(state: LmsLevelState) {
        if (!entitlementManager.hasFullLearningAccess() && !entitlementManager.consumeFreeRecognitionSession()) {
            renderUpgradeScreen("More Letter Recognition practice")
            return
        }
        val sessionLesson = state.lessons.firstOrNull()
        val questions = generateRecognitionQuestions()
        val answers = mutableListOf<Pair<RecognitionQuestion, Char>>()
        var index = 0
        var score = 0
        var answeringLocked = false

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.GONE
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(18))
            background = rounded(0xFF111217.toInt(), null, 0, 14)
        }
        learnList.addView(root, LinearLayout.LayoutParams(-1, -2))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(Button(this).apply {
            text = "Back"
            isAllCaps = false
            textSize = 13f
            setTextColor(Color.WHITE)
            contentDescription = "Back to Learn home"
            background = rounded(0xFF2D3040.toInt(), 0xFF868BE8.toInt(), 1, 10)
            setOnClickListener { loadLearnLessons() }
        }, LinearLayout.LayoutParams(dp(74), dp(48)))
        header.addView(TextView(this).apply {
            text = "Letter Recognition"
            textSize = 22f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, 0, 0)
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        root.addView(header)

        val scoreText = TextView(this).apply {
            text = "Score: 0 out of 10"
            textSize = 16f
            typeface = Typeface.MONOSPACE
            setTextColor(0xFFE6E1FF.toInt())
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, dp(8))
        }
        root.addView(scoreText)

        val instructionText = TextView(this).apply {
            text = "Which letter is this?"
            textSize = 22f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(0, dp(8), 0, dp(14))
        }
        root.addView(instructionText)

        val cellView = BrailleCellView(this).apply {
            showDotNumbers = false
            interactive = false
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
        }
        root.addView(cellView, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(4)
            bottomMargin = dp(16)
        })

        val answerGrid = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        root.addView(answerGrid)

        val feedbackText = TextView(this).apply {
            text = ""
            textSize = 15f
            setTextColor(0xFFECEAF6.toInt())
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.3f)
            setPadding(0, dp(12), 0, dp(12))
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        root.addView(feedbackText)

        root.addView(actionButton("Voice Answer", false) {
            toast("Voice answer coming soon")
        }.apply {
            contentDescription = "Voice answer placeholder. Speech recognition is not available yet."
        }, LinearLayout.LayoutParams(-1, dp(52)).apply {
            topMargin = dp(4)
        })

        lateinit var showQuestion: () -> Unit

        fun saveAnswer(question: RecognitionQuestion, selected: Char, correct: Boolean) {
            if (sessionLesson == null) return
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.saveUserScore(
                        lessonId = sessionLesson.id,
                        questionId = "level-3-${index + 1}-${question.correctAnswer}-${System.currentTimeMillis()}",
                        userAnswer = selected.toString(),
                        correctAnswer = question.correctAnswer.toString(),
                        isCorrect = correct
                    )
                }
            }
        }

        fun finishSession() {
            val accuracy = (score * 100f) / questions.size
            val missedLetters = answers
                .filter { (question, selected) -> selected != question.correctAnswer }
                .map { it.first.correctAnswer }
                .distinct()
                .sorted()
            val suggestions = missedLetters.ifEmpty { listOf('A', 'B', 'C') }

            if (sessionLesson != null) {
                lifecycleScope.launch {
                    withContext(Dispatchers.IO) {
                        lmsRepository.markLessonCompleted(
                            lessonId = sessionLesson.id,
                            level = 3,
                            score = score,
                            accuracy = accuracy
                        )
                    }
                    syncLmsAfterLessonCompletion()
                }
            }

            answerGrid.removeAllViews()
            cellView.visibility = View.GONE
            instructionText.text = "Results"
            scoreText.text = "Score: $score out of ${questions.size}"
            feedbackText.text = buildString {
                append("Accuracy: ${accuracy.roundToInt()}%\n")
                append("Letters missed: ")
                append(if (missedLetters.isEmpty()) "None" else missedLetters.joinToString(", "))
                append("\nSuggested practice: ")
                append(suggestions.joinToString(", "))
            }
            lmsHapticManager.completion()
            lmsAudioManager.speakCorrect("Practice complete. Accuracy ${accuracy.roundToInt()} percent.")
            root.addView(actionButton("Practice Again", true) {
                renderLetterRecognition(state)
            }, LinearLayout.LayoutParams(-1, dp(54)).apply {
                topMargin = dp(12)
            })
            root.addView(actionButton("Back to Learn Home", false) {
                loadLearnLessons()
            }, LinearLayout.LayoutParams(-1, dp(54)).apply {
                topMargin = dp(10)
            })
        }

        fun handleAnswer(question: RecognitionQuestion, selected: Char) {
            if (answeringLocked) return
            answeringLocked = true
            val correct = selected == question.correctAnswer
            answers.add(question to selected)
            if (correct) {
                score += 1
                lmsHapticManager.success()
                feedbackText.text = "Correct. This is letter ${question.correctAnswer}."
                lmsAudioManager.speakCorrect("Correct. This is letter ${question.correctAnswer}.")
            } else {
                lmsHapticManager.error()
                val dots = BrailleMappings.getDotsForLetter(question.correctAnswer)
                feedbackText.text = "Not quite. This is letter ${question.correctAnswer}. It uses ${dotPhrase(dots)}."
                lmsAudioManager.speakIncorrect("Not quite. This is letter ${question.correctAnswer}. It uses ${dotPhrase(dots)}.")
            }
            saveAnswer(question, selected, correct)
            scoreText.text = "Score: $score out of ${questions.size}"
            mainHandler.postDelayed({
                index += 1
                answeringLocked = false
                if (index >= questions.size) finishSession() else showQuestion()
            }, 1100L)
        }

        showQuestion = {
            val question = questions[index]
            val dots = BrailleMappings.getDotsForLetter(question.correctAnswer)
            instructionText.text = "Which letter is this?"
            feedbackText.text = "Question ${index + 1} of ${questions.size}"
            scoreText.text = "Score: $score out of ${questions.size}"
            cellView.visibility = View.VISIBLE
            cellView.activeDots = dots
            cellView.visitedDots = emptySet()
            cellView.contentDescription = "Braille cell with dots ${formatDots(dots)} active."
            answerGrid.removeAllViews()

            question.options.chunked(2).forEach { rowOptions ->
                val row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER
                }
                answerGrid.addView(row, LinearLayout.LayoutParams(-1, -2).apply {
                    bottomMargin = dp(10)
                })
                rowOptions.forEach { option ->
                    row.addView(actionButton(option.toString(), true) {
                        handleAnswer(question, option)
                    }.apply {
                        textSize = 24f
                        contentDescription = "Answer $option"
                    }, LinearLayout.LayoutParams(0, dp(72), 1f).apply {
                        leftMargin = dp(5)
                        rightMargin = dp(5)
                    })
                }
            }
        }

        showQuestion()
        lmsAudioManager.speak("Which letter is this?")
    }

    private fun generateRecognitionQuestions(): List<RecognitionQuestion> {
        return ('A'..'Z').shuffled(Random.Default).take(10).map { correct ->
            val wrong = ('A'..'Z')
                .filter { it != correct }
                .shuffled(Random.Default)
                .take(3)
            RecognitionQuestion(
                correctAnswer = correct,
                options = (wrong + correct).shuffled(Random.Default)
            )
        }
    }

    private fun renderWordReading(state: LmsLevelState) {
        val lessons = state.lessons
            .sortedBy { it.orderIndex }
            .filter { it.id.startsWith("level-4-word-") }
        if (lessons.isEmpty()) {
            toast("Word lessons are not available yet")
            loadLearnLessons()
            return
        }

        var wordIndex = 0
        var letterIndex = 0
        var wordCorrect = 0
        var totalCorrect = 0
        var totalAnswered = 0
        var answeringLocked = false
        var lastInstruction = "Decode each Braille cell from left to right."
        val missedLetters = linkedSetOf<Char>()

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.GONE
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(18))
            background = rounded(0xFF111217.toInt(), null, 0, 14)
        }
        learnList.addView(root, LinearLayout.LayoutParams(-1, -2))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(Button(this).apply {
            text = "Back"
            isAllCaps = false
            textSize = 13f
            setTextColor(Color.WHITE)
            contentDescription = "Back to Learn home"
            background = rounded(0xFF2D3040.toInt(), 0xFF868BE8.toInt(), 1, 10)
            setOnClickListener { loadLearnLessons() }
        }, LinearLayout.LayoutParams(dp(74), dp(48)))
        header.addView(TextView(this).apply {
            text = "Word Reading"
            textSize = 22f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, 0, 0)
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        root.addView(header)

        val progressText = TextView(this).apply {
            textSize = 16f
            typeface = Typeface.MONOSPACE
            setTextColor(0xFFE6E1FF.toInt())
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, dp(8))
        }
        root.addView(progressText)

        val scoreText = TextView(this).apply {
            textSize = 15f
            setTextColor(0xFFECEAF6.toInt())
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(10))
        }
        root.addView(scoreText)

        val instructionText = TextView(this).apply {
            text = "Decode this letter."
            textSize = 21f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.25f)
            setPadding(0, dp(8), 0, dp(14))
        }
        root.addView(instructionText)

        val cellView = BrailleCellView(this).apply {
            showDotNumbers = false
            interactive = false
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
        }
        root.addView(cellView, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(4)
            bottomMargin = dp(16)
        })

        val wordCellsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(14))
        }
        root.addView(wordCellsRow)

        val answerGrid = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        root.addView(answerGrid)

        val feedbackText = TextView(this).apply {
            text = ""
            textSize = 15f
            setTextColor(0xFFECEAF6.toInt())
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.3f)
            setPadding(0, dp(12), 0, dp(12))
        }
        root.addView(feedbackText)

        val controls = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, 0)
        }
        root.addView(controls)

        lateinit var showCurrentCell: () -> Unit
        lateinit var showWordComplete: (LessonEntity, String) -> Unit

        fun currentLesson(): LessonEntity = lessons[wordIndex]
        fun currentWord(): String = currentLesson().id.substringAfter("level-4-word-")
        fun currentLetter(): Char = currentWord()[letterIndex].uppercaseChar()

        fun answerOptions(correct: Char): List<Char> {
            val wrong = ('A'..'Z')
                .filter { it != correct }
                .shuffled(Random.Default)
                .take(3)
            return (wrong + correct).shuffled(Random.Default)
        }

        fun saveCellScore(lesson: LessonEntity, selected: Char, correct: Char, isCorrect: Boolean) {
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.saveUserScore(
                        lessonId = lesson.id,
                        questionId = "${lesson.id}-cell-${letterIndex + 1}-${System.currentTimeMillis()}",
                        userAnswer = selected.toString(),
                        correctAnswer = correct.toString(),
                        isCorrect = isCorrect
                    )
                }
            }
        }

        fun markWordComplete(lesson: LessonEntity, correctCount: Int, wordLength: Int) {
            val accuracy = if (wordLength == 0) 0f else (correctCount * 100f) / wordLength
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.markLessonCompleted(
                        lessonId = lesson.id,
                        level = 4,
                        score = correctCount,
                        accuracy = accuracy
                    )
                }
                syncLmsAfterLessonCompletion()
            }
        }

        fun updateMiniCells(word: String) {
            wordCellsRow.removeAllViews()
            word.forEachIndexed { index, char ->
                val active = index == letterIndex
                wordCellsRow.addView(TextView(this).apply {
                    text = if (index < letterIndex) char.uppercaseChar().toString() else (index + 1).toString()
                    textSize = if (active) 18f else 15f
                    typeface = Typeface.DEFAULT_BOLD
                    gravity = Gravity.CENTER
                    setTextColor(Color.WHITE)
                    background = rounded(
                        if (active) 0xFF584FB9.toInt() else 0xFF242631.toInt(),
                        if (active) 0xFFFFDBCC.toInt() else 0xFF6C718B.toInt(),
                        if (active) 3 else 1,
                        12
                    )
                    contentDescription = if (active) {
                        "Current Braille cell ${index + 1} of ${word.length}"
                    } else if (index < letterIndex) {
                        "Decoded letter ${char.uppercaseChar()}"
                    } else {
                        "Upcoming Braille cell ${index + 1}"
                    }
                }, LinearLayout.LayoutParams(dp(48), dp(48)).apply {
                    leftMargin = dp(4)
                    rightMargin = dp(4)
                })
            }
        }

        fun finishLevel() {
            val accuracy = if (totalAnswered == 0) 0f else (totalCorrect * 100f) / totalAnswered
            answerGrid.removeAllViews()
            wordCellsRow.removeAllViews()
            cellView.visibility = View.GONE
            instructionText.text = "Level 4 Complete"
            progressText.text = "Word ${lessons.size} of ${lessons.size}"
            scoreText.text = "Score: $totalCorrect out of $totalAnswered"
            feedbackText.text = buildString {
                append("Accuracy: ${accuracy.roundToInt()}%\n")
                append("Completed words: ${lessons.size}/${lessons.size}\n")
                append("Letters to practice: ")
                append(if (missedLetters.isEmpty()) "None" else missedLetters.joinToString(", "))
            }
            lastInstruction = "Word Reading complete. Accuracy ${accuracy.roundToInt()} percent."
            lmsHapticManager.completion()
            lmsAudioManager.speakCorrect(lastInstruction)
            root.addView(actionButton("Practice Again", true) {
                renderWordReading(state)
            }, LinearLayout.LayoutParams(-1, dp(54)).apply {
                topMargin = dp(12)
            })
            root.addView(actionButton("Back to Learn Home", false) {
                loadLearnLessons()
            }, LinearLayout.LayoutParams(-1, dp(54)).apply {
                topMargin = dp(10)
            })
        }

        showWordComplete = { lesson, word ->
            val spelling = word.uppercase(Locale.US).toCharArray().joinToString(" ")
            val accuracy = (wordCorrect * 100f) / word.length
            markWordComplete(lesson, wordCorrect, word.length)
            answerGrid.removeAllViews()
            cellView.visibility = View.GONE
            updateMiniCells(word)
            instructionText.text = "The word is ${word.lowercase(Locale.US)}."
            progressText.text = "Word ${wordIndex + 1} of ${lessons.size}"
            scoreText.text = "Word score: $wordCorrect out of ${word.length} (${accuracy.roundToInt()}%)"
            feedbackText.text = "Spelling: $spelling"
            lastInstruction = "The word is ${word.lowercase(Locale.US)}. Spelling: $spelling."
            lmsAudioManager.speakWord(word)
            val nextLabel = if (wordIndex + 1 < lessons.size) "Next Word" else "Finish Level"
            answerGrid.addView(actionButton(nextLabel, true) {
                if (wordIndex + 1 < lessons.size) {
                    wordIndex += 1
                    letterIndex = 0
                    wordCorrect = 0
                    cellView.visibility = View.VISIBLE
                    showCurrentCell()
                } else {
                    finishLevel()
                }
            }.apply {
                contentDescription = if (wordIndex + 1 < lessons.size) {
                    "Next Word"
                } else {
                    "Finish Level 4 Word Reading"
                }
            }, LinearLayout.LayoutParams(-1, dp(56)))
        }

        fun handleAnswer(selected: Char) {
            if (answeringLocked) return
            answeringLocked = true
            val lesson = currentLesson()
            val word = currentWord()
            val correct = currentLetter()
            val isCorrect = selected == correct
            totalAnswered += 1
            if (isCorrect) {
                wordCorrect += 1
                totalCorrect += 1
                lmsHapticManager.success()
                feedbackText.text = "Correct. This letter is $correct."
                lastInstruction = "Correct. This letter is $correct."
                lmsAudioManager.speakCorrect(lastInstruction)
            } else {
                missedLetters.add(correct)
                lmsHapticManager.error()
                val dots = BrailleMappings.getDotsForLetter(correct)
                feedbackText.text = "This letter is $correct. It uses ${dotPhrase(dots)}."
                lastInstruction = "This letter is $correct. It uses ${dotPhrase(dots)}."
                lmsAudioManager.speakIncorrect(lastInstruction)
            }
            saveCellScore(lesson, selected, correct, isCorrect)
            scoreText.text = "Score: $totalCorrect out of $totalAnswered"
            mainHandler.postDelayed({
                letterIndex += 1
                answeringLocked = false
                if (letterIndex >= word.length) {
                    showWordComplete(lesson, word)
                } else {
                    showCurrentCell()
                }
            }, 1150L)
        }

        showCurrentCell = {
            val lesson = currentLesson()
            val word = currentWord()
            val letter = currentLetter()
            val dots = BrailleMappings.getDotsForLetter(letter)
            lifecycleScope.launch {
                withContext(Dispatchers.IO) { lmsRepository.markLessonStarted(lesson.id, 4) }
            }
            progressText.text = "Word ${wordIndex + 1} of ${lessons.size}"
            scoreText.text = "Score: $totalCorrect out of $totalAnswered"
            instructionText.text = "Which letter is this?"
            feedbackText.text = "Guided mode: decode cell ${letterIndex + 1} of ${word.length}."
            lastInstruction = "Word ${wordIndex + 1} of ${lessons.size}. Which letter is this?"
            cellView.visibility = View.VISIBLE
            cellView.activeDots = dots
            cellView.visitedDots = emptySet()
            cellView.contentDescription = "Braille cell with dots ${formatDots(dots)} active."
            updateMiniCells(word)
            answerGrid.removeAllViews()
            answerOptions(letter).chunked(2).forEach { rowOptions ->
                val row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER
                }
                answerGrid.addView(row, LinearLayout.LayoutParams(-1, -2).apply {
                    bottomMargin = dp(10)
                })
                rowOptions.forEach { option ->
                    row.addView(actionButton(option.toString(), true) {
                        handleAnswer(option)
                    }.apply {
                        textSize = 24f
                        contentDescription = "Answer $option"
                    }, LinearLayout.LayoutParams(0, dp(72), 1f).apply {
                        leftMargin = dp(5)
                        rightMargin = dp(5)
                    })
                }
            }
        }

        controls.addView(actionButton("Repeat", false) {
            lmsAudioManager.repeatLast()
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        controls.addView(actionButton("Challenge", false) {
            toast("Challenge mode coming soon")
        }.apply {
            contentDescription = "Challenge mode placeholder. Guided mode is available now."
        }, LinearLayout.LayoutParams(0, dp(54), 1f))

        showCurrentCell()
        lmsAudioManager.speak(lastInstruction)
    }

    private fun renderGrade2ContractionsList(state: LmsLevelState) {
        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Grade 2 Contractions"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(TextView(this).apply {
            text = "Grade 2 Contractions"
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(8))
        })
        learnList.addView(TextView(this).apply {
            text = "Learn common contracted Braille words used in real books. This catalog is structured so more contractions can be added later."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            setLineSpacing(0f, 1.35f)
            setPadding(0, 0, 0, dp(14))
        })

        lifecycleScope.launch {
            val progress = withContext(Dispatchers.IO) { lmsRepository.getAllProgress() }
            val progressByLessonId = progress.associateBy { it.lessonId }
            state.lessons.sortedBy { it.orderIndex }.forEach { lesson ->
                val contraction = contractionFromLesson(lesson) ?: return@forEach
                val status = progressByLessonId[lesson.id]?.status ?: LessonProgressStatus.NOT_STARTED
                learnList.addView(contractionLessonCard(contraction, lesson, status), LinearLayout.LayoutParams(-1, -2).apply {
                    bottomMargin = dp(10)
                })
            }
        }
    }

    private fun contractionLessonCard(
        contraction: Grade2Contraction,
        lesson: LessonEntity,
        status: String
    ): View {
        val statusText = when (status) {
            LessonProgressStatus.COMPLETED -> "Completed"
            LessonProgressStatus.IN_PROGRESS -> "In progress"
            else -> "Not started"
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(16), dp(14), dp(16), dp(14))
            contentDescription = "Contraction ${contraction.contractionText}, ${contraction.displaySymbol}, means ${contraction.meaning}, $statusText"
            setOnClickListener { renderGrade2ContractionLesson(lesson, contraction) }
            addView(TextView(context).apply {
                text = contraction.contractionText.uppercase(Locale.US)
                textSize = 18f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setTextColor(ScioColors.TEXT)
                background = rounded(ScioColors.SURFACE_CONTAINER, ScioColors.OUTLINE, 1, 12)
                contentDescription = "Contraction text ${contraction.contractionText}"
            }, LinearLayout.LayoutParams(dp(92), dp(62)))
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(14), 0, 0, 0)
                addView(TextView(context).apply {
                    text = contraction.meaning.replaceFirstChar { it.uppercase() }
                    textSize = 17f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(ScioColors.TEXT)
                })
                addView(TextView(context).apply {
                    text = "${contraction.displaySymbol} - $statusText"
                    textSize = 14f
                    setTextColor(ScioColors.MUTED)
                    setPadding(0, dp(4), 0, 0)
                })
            }, LinearLayout.LayoutParams(0, -2, 1f))
            addView(TextView(context).apply {
                text = "Open"
                textSize = 13f
                typeface = Typeface.MONOSPACE
                setTextColor(ScioColors.SECONDARY)
                gravity = Gravity.CENTER
            }, LinearLayout.LayoutParams(dp(54), dp(48)))
        }
    }

    private fun renderGrade2ContractionLesson(
        lesson: LessonEntity,
        contraction: Grade2Contraction
    ) {
        var answered = false
        var lastInstruction = contractionExplanation(contraction)

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.GONE
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(18))
            background = rounded(0xFF111217.toInt(), null, 0, 14)
        }
        learnList.addView(root, LinearLayout.LayoutParams(-1, -2))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(Button(this).apply {
            text = "Back"
            isAllCaps = false
            textSize = 13f
            setTextColor(Color.WHITE)
            contentDescription = "Back to Grade 2 Contractions list"
            background = rounded(0xFF2D3040.toInt(), 0xFF868BE8.toInt(), 1, 10)
            setOnClickListener {
                lifecycleScope.launch {
                    val lessons = withContext(Dispatchers.IO) {
                        lmsRepository.seedDefaultCurriculumIfNeeded()
                        lmsRepository.getLessonsByLevel(5)
                    }
                    renderGrade2ContractionsList(
                        stateForLevelFive(lessons)
                    )
                }
            }
        }, LinearLayout.LayoutParams(dp(74), dp(48)))
        header.addView(TextView(this).apply {
            text = "Grade 2 Contractions"
            textSize = 21f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, 0, 0)
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        root.addView(header)

        root.addView(TextView(this).apply {
            text = contraction.contractionText.uppercase(Locale.US)
            textSize = 34f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(0, dp(20), 0, dp(8))
            contentDescription = "Contraction text ${contraction.contractionText}"
        })

        val cellsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            background = rounded(0xFF1C1D26.toInt(), 0xFF5C6075.toInt(), 1, 18)
            setPadding(dp(14), dp(14), dp(14), dp(14))
            contentDescription = "Braille contraction pattern ${contraction.displaySymbol}"
        }
        root.addView(cellsRow, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(8)
            bottomMargin = dp(16)
        })
        contraction.cells.forEachIndexed { index, dots ->
            cellsRow.addView(BrailleCellView(this).apply {
                activeDots = dots
                visitedDots = dots
                showDotNumbers = true
                interactive = false
                contentDescription = "Braille cell ${index + 1}, dots ${formatDots(dots)} active, contraction ${contraction.contractionText}"
            }, LinearLayout.LayoutParams(0, -2, 1f).apply {
                leftMargin = dp(4)
                rightMargin = dp(4)
            })
        }

        val explanationText = TextView(this).apply {
            text = buildString {
                append("${contraction.contractionText.uppercase(Locale.US)} means ${contraction.meaning}.\n")
                append("${contraction.displaySymbol}.\n")
                append("Example: ${contraction.exampleSentence}")
            }
            textSize = 17f
            setTextColor(0xFFECEAF6.toInt())
            setLineSpacing(0f, 1.35f)
            setPadding(0, 0, 0, dp(14))
            contentDescription = text
        }
        root.addView(explanationText)

        val feedbackText = TextView(this).apply {
            text = "Practice: What does this contraction mean?"
            textSize = 17f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.25f)
            setPadding(0, dp(6), 0, dp(12))
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        root.addView(feedbackText)

        val answerGrid = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        root.addView(answerGrid)

        fun answerOptions(): List<String> {
            val wrong = Grade2Contractions.initialSet
                .map { it.contractionText }
                .filter { it != contraction.contractionText }
                .shuffled(Random.Default)
                .take(3)
            return (wrong + contraction.contractionText).shuffled(Random.Default)
        }

        fun finishAnswer(selected: String) {
            if (answered) return
            answered = true
            val correct = selected.equals(contraction.contractionText, ignoreCase = true)
            if (correct) {
                lmsHapticManager.success()
                feedbackText.text = "Correct. This contraction means ${contraction.meaning}."
                lastInstruction = "Correct. This contraction means ${contraction.meaning}."
                lmsAudioManager.speakCorrect(lastInstruction)
            } else {
                lmsHapticManager.error()
                feedbackText.text = "Not quite. This contraction means ${contraction.meaning}. It is written with ${contraction.displaySymbol}."
                lastInstruction = "Not quite. This contraction means ${contraction.meaning}. It is written with ${contraction.displaySymbol}."
                lmsAudioManager.speakIncorrect(lastInstruction)
            }
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.saveUserScore(
                        lessonId = lesson.id,
                        questionId = "${lesson.id}-practice-${System.currentTimeMillis()}",
                        userAnswer = selected,
                        correctAnswer = contraction.contractionText,
                        isCorrect = correct
                    )
                    lmsRepository.markLessonCompleted(
                        lessonId = lesson.id,
                        level = 5,
                        score = if (correct) 1 else 0,
                        accuracy = if (correct) 100f else 0f
                    )
                }
                syncLmsAfterLessonCompletion()
            }
            answerGrid.addView(actionButton("Back to List", false) {
                lifecycleScope.launch {
                    val lessons = withContext(Dispatchers.IO) { lmsRepository.getLessonsByLevel(5) }
                    renderGrade2ContractionsList(stateForLevelFive(lessons))
                }
            }, LinearLayout.LayoutParams(-1, dp(54)).apply {
                topMargin = dp(12)
            })
        }

        answerOptions().chunked(2).forEach { rowOptions ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }
            answerGrid.addView(row, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
            rowOptions.forEach { option ->
                row.addView(actionButton(option, true) {
                    finishAnswer(option)
                }.apply {
                    textSize = 17f
                    contentDescription = "Answer $option"
                }, LinearLayout.LayoutParams(0, dp(68), 1f).apply {
                    leftMargin = dp(5)
                    rightMargin = dp(5)
                })
            }
        }

        root.addView(actionButton("Repeat Explanation", false) {
            lmsAudioManager.repeatLast()
        }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            topMargin = dp(4)
        })

        lifecycleScope.launch {
            withContext(Dispatchers.IO) { lmsRepository.markLessonStarted(lesson.id, 5) }
        }
        lmsAudioManager.speak(lastInstruction)
    }

    private fun stateForLevelFive(lessons: List<LessonEntity>): LmsLevelState {
        return LmsLevelState(
            level = 5,
            title = "Grade 2 Contractions",
            description = "Learn common contractions used in real Braille books.",
            cta = "Learn",
            progressPercent = 0,
            completedLessons = 0,
            totalLessons = lessons.size,
            unlocked = true,
            lockedReason = "",
            lessons = lessons.sortedBy { it.orderIndex }
        )
    }

    private fun contractionFromLesson(lesson: LessonEntity): Grade2Contraction? {
        val content = runCatching { LessonContent.fromJson(lesson.contentJson) }.getOrNull()
        val contractionText = content?.contraction ?: lesson.id.substringAfter("level-5-contraction-", "")
        return Grade2Contractions.byText(contractionText)
            ?: Grade2Contractions.byId(contractionText)
            ?: content?.let {
                val cells = if (it.cells.isNotEmpty()) {
                    it.cells.map { cell -> cell.toSet() }
                } else {
                    listOf(it.dots.toSet())
                }
                Grade2Contraction(
                    id = lesson.id.substringAfter("level-5-contraction-", contractionText),
                    contractionText = contractionText,
                    displaySymbol = it.displaySymbol ?: "dots ${formatDots(cells.firstOrNull().orEmpty())}",
                    cells = cells,
                    meaning = it.meaning ?: "the word $contractionText",
                    exampleSentence = it.exampleSentence ?: "Read the word $contractionText.",
                    grade = it.grade ?: 2,
                    orderIndex = lesson.orderIndex
                )
            }
    }

    private fun contractionExplanation(contraction: Grade2Contraction): String {
        return "The contraction ${contraction.contractionText.uppercase(Locale.US)} means ${contraction.meaning}. " +
            "It is one of the common Braille contractions. It is written with ${contraction.displaySymbol}. " +
            "Example: ${contraction.exampleSentence}"
    }

    private fun renderScanAndLearnIntro(state: LmsLevelState) {
        val practiceCount = getSharedPreferences("sciobraille", MODE_PRIVATE)
            .getString("scan_practice_sessions", "[]")
            .orEmpty()
            .let { raw -> runCatching { JSONArray(raw).length() }.getOrDefault(0) }

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Scan and Learn"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        scanPracticeLessonId = state.lessons
            .firstOrNull { it.id == "level-6-scan-own-page" }
            ?.id
            ?: state.lessons.firstOrNull()?.id
            ?: "level-6-scan-own-page"

        learnList.addView(actionButton("Back to Learn Home", false) { loadLearnLessons() }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })
        learnList.addView(TextView(this).apply {
            text = "Scan and Learn"
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(8))
        })
        learnList.addView(TextView(this).apply {
            text = "Use the existing Sciobraille scanner as real-world practice. Scan Braille, then review each detected cell with audio explanations."
            textSize = 16f
            setTextColor(ScioColors.MUTED)
            setLineSpacing(0f, 1.35f)
            setPadding(0, 0, 0, dp(14))
        })
        learnList.addView(TextView(this).apply {
            text = "Practice sessions saved: $practiceCount"
            textSize = 15f
            typeface = Typeface.MONOSPACE
            setTextColor(ScioColors.TEXT)
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
            setPadding(dp(14), dp(12), dp(14), dp(12))
            contentDescription = "$practiceCount scan practice sessions saved"
        }, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(14)
        })
        learnList.addView(actionButton("Start Scan Practice", true) {
            startScanPracticeFromLearn()
        }.apply {
            contentDescription = "Start Scan Practice. Opens the scanner and waits for a stable Braille detection."
        }, LinearLayout.LayoutParams(-1, dp(58)))
    }

    private fun startScanPracticeFromLearn() {
        scanPracticePending = true
        showTab(AppTab.SCANNER)
        outputText.text = "Scan practice is active. Point the camera at Braille."
        braillePreviewText.text = ""
        frameOverlay.setStatus("Scan practice", false)
        if (!isScanning) startScanning()
    }

    private fun renderScanPracticeResult(payload: ScannerPayload) {
        stopScanning("Practice captured")
        showTab(AppTab.LEARN)

        val detectedText = payload.text.trim()
        val cells = cellsFromDetectedText(detectedText)
        var cellIndex = 0
        var explainedCells = 0
        val confidenceLabel = confidenceLabel(payload.confidence)
        var lastInstruction = if (cells.isNotEmpty()) {
            cellExplanation(cells.first())
        } else {
            "Detected text: $detectedText"
        }

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.VISIBLE
        learnStatusText.text = "Scan Practice Result"
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        learnList.addView(actionButton("Back to Scan and Learn", false) {
            lifecycleScope.launch {
                val lessons = withContext(Dispatchers.IO) { lmsRepository.getLessonsByLevel(6) }
                renderScanAndLearnIntro(
                    LmsLevelState(
                        level = 6,
                        title = "Scan and Learn",
                        description = "Scan real Braille and learn from detected cells.",
                        cta = "Scan Practice",
                        progressPercent = 0,
                        completedLessons = 0,
                        totalLessons = lessons.size,
                        unlocked = true,
                        lockedReason = "",
                        lessons = lessons
                    )
                )
            }
        }, LinearLayout.LayoutParams(-1, dp(54)).apply {
            bottomMargin = dp(16)
        })

        learnList.addView(TextView(this).apply {
            text = "Scan and Learn"
            textSize = 26f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            setPadding(0, dp(4), 0, dp(8))
        })
        learnList.addView(TextView(this).apply {
            val confidenceMessage = "Detection confidence: $confidenceLabel. ${if (confidenceLabel == "low") "Please scan again with better lighting." else "Ready for practice."}"
            setText(confidenceMessage)
            textSize = 15f
            typeface = Typeface.MONOSPACE
            setTextColor(if (confidenceLabel == "low") ScioColors.ERROR else ScioColors.TEXT)
            background = rounded(ScioColors.SURFACE, if (confidenceLabel == "low") ScioColors.ERROR else ScioColors.OUTLINE, 1, 8)
            setPadding(dp(14), dp(12), dp(14), dp(12))
            contentDescription = confidenceMessage
        }, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(14)
        })

        learnList.addView(TextView(this).apply {
            setText("Detected text\n$detectedText")
            textSize = 19f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(ScioColors.TEXT)
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(16), dp(14), dp(16), dp(14))
            contentDescription = "Detected text: ${detectedText.replace("\n", ". ")}"
        }, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(14)
        })

        val cellHost = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(0xFF111217.toInt(), null, 0, 14)
            setPadding(dp(16), dp(16), dp(16), dp(16))
        }
        learnList.addView(cellHost, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(14)
        })

        val wordText = TextView(this).apply {
            textSize = 16f
            setTextColor(0xFFECEAF6.toInt())
            setLineSpacing(0f, 1.3f)
            setPadding(0, 0, 0, dp(12))
        }
        cellHost.addView(wordText)

        val cellView = BrailleCellView(this).apply {
            showDotNumbers = true
            interactive = false
        }
        cellHost.addView(cellView, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(12)
        })

        val explanationText = TextView(this).apply {
            textSize = 17f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.25f)
            setPadding(0, 0, 0, dp(12))
        }
        cellHost.addView(explanationText)

        fun refreshCell() {
            if (cells.isEmpty()) {
                wordText.text = "Braille cells detected: 0"
                cellView.visibility = View.GONE
                explanationText.text = "No Grade 1 letter cells could be explained from this scan."
                lastInstruction = "No Grade 1 letter cells could be explained from this scan."
                return
            }
            val cell = cells[cellIndex]
            val wordLength = cell.word.length
            wordText.text = "Braille cells detected: ${cells.size}\nWord: ${cell.word}. This word has $wordLength ${if (wordLength == 1) "letter" else "letters"}."
            cellView.visibility = View.VISIBLE
            cellView.activeDots = cell.dots
            cellView.visitedDots = cell.dots
            cellView.contentDescription = "Cell ${cell.index} is letter ${cell.letter}. Dots ${formatDots(cell.dots)} active."
            explanationText.text = cellExplanation(cell)
            lastInstruction = cellExplanation(cell)
        }

        val controls = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        learnList.addView(controls, LinearLayout.LayoutParams(-1, -2).apply {
            bottomMargin = dp(10)
        })

        controls.addView(actionButton("Explain first cell", true) {
            if (cells.isNotEmpty()) {
                cellIndex = 0
                explainedCells = max(explainedCells, 1)
                refreshCell()
            }
            lmsAudioManager.speak(lastInstruction)
        }, LinearLayout.LayoutParams(0, dp(58), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        controls.addView(actionButton("Next cell", true) {
            if (cells.isNotEmpty()) {
                cellIndex = (cellIndex + 1).coerceAtMost(cells.lastIndex)
                explainedCells = max(explainedCells, cellIndex + 1)
                refreshCell()
            }
            lmsAudioManager.repeatLast()
        }, LinearLayout.LayoutParams(0, dp(58), 1f))

        val controlsTwo = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        learnList.addView(controlsTwo, LinearLayout.LayoutParams(-1, -2))
        controlsTwo.addView(actionButton("Read full text", true) {
            val spoken = "Detected text: ${detectedText.replace("\n", ". ")}"
            lmsAudioManager.speak(spoken)
        }, LinearLayout.LayoutParams(0, dp(58), 1f))
        controlsTwo.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        controlsTwo.addView(actionButton("Save practice", true) {
            saveScanPracticeSession(payload, cells, max(explainedCells, if (cells.isNotEmpty()) cellIndex + 1 else 0))
        }, LinearLayout.LayoutParams(0, dp(58), 1f))

        refreshCell()
        lmsAudioManager.speak(lastInstruction)
    }

    private fun cellsFromDetectedText(text: String): List<ScanPracticeCell> {
        val cells = mutableListOf<ScanPracticeCell>()
        var index = 1
        text.lines()
            .flatMap { it.split(Regex("\\s+")) }
            .filter { it.isNotBlank() }
            .forEach { rawWord ->
                val word = rawWord.filter { it.isLetter() }.lowercase(Locale.US)
                word.forEachIndexed { letterIndex, char ->
                    val dots = BrailleMappings.getDotsForLetter(char)
                    if (dots.isNotEmpty()) {
                        cells.add(
                            ScanPracticeCell(
                                index = index,
                                letter = char.uppercaseChar(),
                                dots = dots,
                                word = word,
                                positionInWord = letterIndex + 1
                            )
                        )
                        index += 1
                    }
                }
            }
        return cells
    }

    private fun cellExplanation(cell: ScanPracticeCell): String {
        return "Cell ${cell.index} is letter ${cell.letter}. It uses ${dotPhrase(cell.dots)}."
    }

    private fun confidenceLabel(confidence: Double): String {
        return when {
            confidence >= 0.75 -> "high"
            confidence >= 0.45 -> "medium"
            else -> "low"
        }
    }

    private fun saveScanPracticeSession(
        payload: ScannerPayload,
        cells: List<ScanPracticeCell>,
        explainedCells: Int
    ) {
        val words = payload.text
            .trim()
            .lines()
            .flatMap { it.split(Regex("\\s+")) }
            .map { it.filter { char -> char.isLetter() }.lowercase(Locale.US) }
            .filter { it.isNotBlank() }
            .distinct()
        val timestamp = System.currentTimeMillis()
        val session = JSONObject().apply {
            put("id", "scan-practice-$timestamp")
            put("lessonId", scanPracticeLessonId)
            put("detectedText", payload.text.trim())
            put("detections", payload.detections)
            put("confidence", payload.confidence)
            put("scansCompleted", 1)
            put("cellsExplained", explainedCells.coerceIn(0, cells.size))
            put("detectedWordsPracticed", JSONArray(words))
            put("createdAt", timestamp)
        }
        val prefs = getSharedPreferences("sciobraille", MODE_PRIVATE)
        val existing = runCatching {
            JSONArray(prefs.getString("scan_practice_sessions", "[]").orEmpty())
        }.getOrElse { JSONArray() }
        existing.put(session)
        prefs.edit().putString("scan_practice_sessions", existing.toString()).apply()

        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                lmsRepository.saveUserScore(
                    lessonId = scanPracticeLessonId,
                    questionId = "scan-practice-$timestamp",
                    userAnswer = payload.text.trim(),
                    correctAnswer = words.joinToString(" "),
                    isCorrect = payload.text.isNotBlank()
                )
                lmsRepository.markLessonCompleted(
                    lessonId = scanPracticeLessonId,
                    level = 6,
                    score = explainedCells,
                    accuracy = (payload.confidence * 100f).toFloat().coerceIn(0f, 100f)
                )
            }
            syncLmsAfterLessonCompletion()
            toast("Scan practice saved")
            lmsAudioManager.speakCorrect("Scan practice saved.")
            loadLearnLessons()
        }
    }

    private fun renderDotExplorer(state: LmsLevelState) {
        val visitedDots = linkedSetOf<Int>()
        lmsAudioManager.setAutoSpeak(true)
        var lastInstruction = "Explore all six dots. Tap each dot to hear its position."

        learnTitleText.visibility = View.GONE
        learnSubtitleText.visibility = View.GONE
        learnStatusText.visibility = View.GONE
        learnList.removeAllViews()
        learnList.setPadding(0, 0, 0, 0)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(18))
            background = rounded(0xFF111217.toInt(), null, 0, 14)
        }
        learnList.addView(root, LinearLayout.LayoutParams(-1, -2))

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val backButton = Button(this).apply {
            text = "Back"
            isAllCaps = false
            textSize = 13f
            setTextColor(Color.WHITE)
            contentDescription = "Back to Learn home"
            background = rounded(0xFF2D3040.toInt(), 0xFF868BE8.toInt(), 1, 10)
            setOnClickListener { loadLearnLessons() }
        }
        header.addView(backButton, LinearLayout.LayoutParams(dp(74), dp(48)))
        header.addView(TextView(this).apply {
            text = "Braille Basics"
            textSize = 22f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, dp(8), 0)
        }, LinearLayout.LayoutParams(0, dp(48), 1f))
        val progressText = TextView(this).apply {
            text = "0% complete"
            textSize = 12f
            typeface = Typeface.MONOSPACE
            setTextColor(0xFFE6E1FF.toInt())
            gravity = Gravity.CENTER
        }
        header.addView(progressText, LinearLayout.LayoutParams(dp(92), dp(48)))
        val voiceButton = Button(this).apply {
            text = "Voice On"
            isAllCaps = false
            textSize = 12f
            setTextColor(Color.WHITE)
            contentDescription = "Voice button, auto speak on"
            background = rounded(0xFF584FB9.toInt(), 0xFFE3DFFF.toInt(), 1, 10)
        }
        header.addView(voiceButton, LinearLayout.LayoutParams(dp(92), dp(48)))
        root.addView(header)

        val dotCell = BrailleCellView(this).apply {
            this.activeDots = emptySet()
            this.visitedDots = emptySet()
            this.showDotNumbers = true
            this.interactive = true
        }
        root.addView(dotCell, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(22)
        })

        val instructionText = TextView(this).apply {
            text = "Explore all six dots (0/6)"
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setLineSpacing(0f, 1.2f)
        }
        val bottomCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(0xFF1C1D26.toInt(), 0xFF5C6075.toInt(), 1, 18)
            setPadding(dp(18), dp(18), dp(18), dp(18))
        }
        root.addView(bottomCard, LinearLayout.LayoutParams(-1, -2).apply {
            topMargin = dp(18)
        })
        bottomCard.addView(instructionText, LinearLayout.LayoutParams(-1, -2))
        val controls = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, 0)
        }
        bottomCard.addView(controls, LinearLayout.LayoutParams(-1, -2))

        lateinit var continueButton: Button
        lateinit var refreshUi: () -> Unit

        fun handleDot(dot: Int) {
            visitedDots.add(dot)
            lastInstruction = dotInstruction(dot)
            lmsHapticManager.dot(dot)
            lmsAudioManager.speakDot(dot)
            refreshUi()
        }

        dotCell.onDotClick = ::handleDot

        controls.addView(actionButton("Repeat", false) {
            lmsAudioManager.repeatLast()
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        controls.addView(actionButton("Reset", false) {
            visitedDots.clear()
            lastInstruction = "Explore all six dots. Tap each dot to hear its position."
            refreshUi()
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        controls.addView(SpaceView(this), LinearLayout.LayoutParams(dp(10), 1))
        continueButton = actionButton("Continue", true) {
            if (visitedDots.size < 6) {
                toast("Explore all six dots first")
                return@actionButton
            }
            lifecycleScope.launch {
                withContext(Dispatchers.IO) {
                    lmsRepository.markLessonCompleted(
                        lessonId = "level-1-dot-explorer",
                        level = 1,
                        score = 100,
                        accuracy = 100f
                    )
                }
                syncLmsAfterLessonCompletion()
                lmsHapticManager.completion()
                lmsAudioManager.speakCorrect("Dot Explorer complete.")
                loadLearnLessons()
            }
        }
        controls.addView(continueButton, LinearLayout.LayoutParams(0, dp(54), 1f))

        voiceButton.setOnClickListener {
            val autoSpeak = lmsAudioManager.toggleAutoSpeak()
            voiceButton.text = if (autoSpeak) "Voice On" else "Voice Off"
            voiceButton.contentDescription = "Voice button, auto speak ${if (autoSpeak) "on" else "off"}"
            voiceButton.background = rounded(
                if (autoSpeak) 0xFF584FB9.toInt() else 0xFF2D3040.toInt(),
                0xFFE3DFFF.toInt(),
                1,
                10
            )
            toast(if (autoSpeak) "Auto speak on" else "Auto speak off")
        }

        refreshUi = {
            val count = visitedDots.size
            val percent = ((count * 100f) / 6f).roundToInt()
            progressText.text = "$percent% complete"
            instructionText.text = "Explore all six dots ($count/6)"
            continueButton.alpha = if (count == 6) 1f else 0.45f
            continueButton.isEnabled = count == 6
            continueButton.contentDescription = if (count == 6) {
                "Continue, complete Dot Explorer"
            } else {
                "Continue locked. Explore all six dots first. $count of 6 complete."
            }
            dotCell.activeDots = emptySet()
            dotCell.visitedDots = visitedDots
        }

        refreshUi()
        lmsAudioManager.speak(lastInstruction)
    }

    private fun dotInstruction(dot: Int): String {
        return "This is dot $dot, ${dotPositionLabel(dot)}."
    }

    private fun dotPositionLabel(dot: Int): String {
        return when (dot) {
            1 -> "left column, top row"
            2 -> "left column, middle row"
            3 -> "left column, bottom row"
            4 -> "right column, top row"
            5 -> "right column, middle row"
            6 -> "right column, bottom row"
            else -> "unknown position"
        }
    }

    private fun levelContentDescription(state: LmsLevelState): String {
        val status = if (state.unlocked) "Unlocked" else "Locked. ${state.lockedReason}"
        return "Level ${state.level}, ${state.title}. ${state.description} Progress ${state.progressPercent} percent. " +
            "${state.completedLessons} of ${state.totalLessons} lessons completed. $status. Button ${state.cta}."
    }

    private fun startCamera() {
        val providerFuture = ProcessCameraProvider.getInstance(this)
        providerFuture.addListener(
            {
                runCatching {
                    val provider = providerFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    imageCapture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .setJpegQuality(75)
                        .build()
                    provider.unbindAll()
                    camera = provider.bindToLifecycle(
                        this,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageCapture
                    )
                }.onSuccess {
                    frameOverlay.setStatus("Ready", false)
                }.onFailure {
                    imageCapture = null
                    camera = null
                    frameOverlay.setStatus("Camera unavailable", false)
                }
            },
            ContextCompat.getMainExecutor(this)
        )
    }

    private fun startScanning() {
        if (!hasCameraPermission()) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                CAMERA_PERMISSION_REQUEST
            )
            return
        }
        if (imageCapture == null) {
            frameOverlay.setStatus("Camera is not ready", false)
            startCamera()
            return
        }
        isScanning = true
        pendingFrames = 0
        pendingSinceMs = 0L
        fallbackDetector.resetSession()
        openScanSocket()
        scanButton.text = "Stop"
        progress.visibility = View.VISIBLE
        statsText.text = "0 cells / 0% confidence / Scanning"
        frameOverlay.setStatus("Connecting...", true)
        mainHandler.removeCallbacks(scanLoop)
        mainHandler.post(scanLoop)
    }

    private fun stopScanning(message: String) {
        isScanning = false
        isFrameInFlight = false
        pendingFrames = 0
        fallbackDetector.resetSession()
        webSocket?.close(1000, "Stopped")
        webSocket = null
        progress.visibility = View.GONE
        scanButton.text = "Scan"
        frameOverlay.setStatus(message, false)
        mainHandler.removeCallbacks(scanLoop)
    }

    private fun openScanSocket() {
        lastSocketAttemptMs = System.currentTimeMillis()
        val request = Request.Builder().url(scanSocketUrl()).build()
        webSocket = httpClient.newWebSocket(
            request,
            object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    runOnUiThread {
                        if (isScanning) frameOverlay.setStatus("Scanning Braille...", true)
                    }
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    pendingFrames = max(0, pendingFrames - 1)
                    if (pendingFrames == 0) pendingSinceMs = 0L
                    val payload = ScannerPayload.fromJsonOrNull(text)
                    runOnUiThread {
                        if (payload == null) {
                            frameOverlay.setStatus("Invalid server response. Using device fallback.", false)
                            this@MainActivity.webSocket?.cancel()
                            this@MainActivity.webSocket = null
                        } else {
                            renderPayload(payload)
                        }
                    }
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    pendingFrames = 0
                    pendingSinceMs = 0L
                    this@MainActivity.webSocket = null
                    runOnUiThread {
                        if (isScanning) frameOverlay.setStatus("Device fallback", true)
                    }
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    pendingFrames = 0
                    pendingSinceMs = 0L
                    this@MainActivity.webSocket = null
                }
            }
        )
    }

    private fun scanSocketUrl(): String {
        val baseUrl = BuildConfig.SCIOBRAILLE_BACKEND_URL.trimEnd('/')
        val socketBase = when {
            baseUrl.startsWith("https://") -> "wss://" + baseUrl.removePrefix("https://")
            baseUrl.startsWith("http://") -> "ws://" + baseUrl.removePrefix("http://")
            else -> baseUrl
        }
        return "$socketBase/ws/scan"
    }

    private fun captureAndScan() {
        val capture = imageCapture ?: return
        if (isFrameInFlight) return
        if (webSocket != null && pendingFrames >= MAX_IN_FLIGHT_FRAMES) {
            if (pendingSinceMs > 0L && System.currentTimeMillis() - pendingSinceMs >= SOCKET_RESPONSE_TIMEOUT_MS) {
                webSocket?.cancel()
                webSocket = null
                pendingFrames = 0
                pendingSinceMs = 0L
                frameOverlay.setStatus("Server timeout. Using device fallback.", false)
            } else {
                return
            }
        }
        if (webSocket == null && System.currentTimeMillis() - lastSocketAttemptMs > 3500) {
            openScanSocket()
        }
        isFrameInFlight = true
        progress.visibility = View.VISIBLE

        val frameFile = File.createTempFile("sciobraille-frame", ".jpg", cacheDir)
        val outputOptions = ImageCapture.OutputFileOptions.Builder(frameFile).build()
        capture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                    networkExecutor.execute {
                        try {
                            val bytes = frameFile.readBytes()
                            val sent = webSocket?.send(bytes.toByteString()) == true
                            if (sent) {
                                if (pendingFrames == 0) pendingSinceMs = System.currentTimeMillis()
                                pendingFrames += 1
                            } else {
                                val payload = fallbackDetector.detect(frameFile)
                                runOnUiThread {
                                    renderPayload(payload)
                                    frameOverlay.setStatus("Offline fallback", true)
                                }
                            }
                        } catch (error: Exception) {
                            runOnUiThread { frameOverlay.setStatus(error.message ?: "Scan failed", false) }
                        } finally {
                            frameFile.delete()
                            runOnUiThread {
                                isFrameInFlight = false
                                progress.visibility = View.GONE
                            }
                        }
                    }
                }

                override fun onError(exception: ImageCaptureException) {
                    frameFile.delete()
                    isFrameInFlight = false
                    progress.visibility = View.GONE
                    frameOverlay.setStatus(exception.message ?: "Camera capture failed", false)
                }
            }
        )
    }

    private fun renderPayload(payload: ScannerPayload) {
        if (!payload.ok) {
            frameOverlay.setStatus("Backend error", false)
            return
        }
        detectionOverlay.update(payload.boxes)
        val confidencePercent = (payload.confidence * 100).roundToInt()
        statsText.text = "${payload.detections} cells / $confidencePercent% confidence / ${if (payload.stable) "Stable" else "Scanning"}"
        if (payload.text.isNotBlank()) {
            lastOutput = payload.text.trim()
            outputText.text = lastOutput
            braillePreviewText.text = toBraillePreview(lastOutput)
            if (payload.stable) addHistoryIfNew(payload)
            if (scanPracticePending && payload.stable) {
                scanPracticePending = false
                renderScanPracticeResult(payload)
                return
            }
        } else {
            outputText.text = "Hold steady. No Braille detected yet."
            braillePreviewText.text = ""
        }
        frameOverlay.setStatus(if (payload.stable) "Stable reading" else "Scanning Braille...", true)
    }

    private fun addHistoryIfNew(payload: ScannerPayload) {
        val text = payload.text.trim()
        if (text.isBlank() || text == lastHistoryText) return
        lastHistoryText = text
        historyEntries.add(
            0,
            HistoryEntry(
                text = text,
                braille = toBraillePreview(text),
                detections = payload.detections,
                confidence = payload.confidence,
                createdAt = System.currentTimeMillis()
            )
        )
        while (historyEntries.size > 50) historyEntries.removeAt(historyEntries.lastIndex)
        saveHistory()
    }

    private fun rebuildHistory(query: String) {
        if (!::historyList.isInitialized) return
        historyList.removeAllViews()
        val filtered = historyEntries.filter {
            query.isBlank() || it.text.contains(query, ignoreCase = true)
        }
        if (filtered.isEmpty()) {
            historyList.addView(TextView(this).apply {
                text = "No scans yet. Use Scanner to create your first transcript."
                setTextColor(ScioColors.MUTED)
                textSize = 16f
                gravity = Gravity.CENTER
                background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 12)
                setPadding(dp(20), dp(28), dp(20), dp(28))
            }, LinearLayout.LayoutParams(-1, -2))
            return
        }
        filtered.forEach { entry ->
            historyList.addView(historyCard(entry), LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(18)
            })
        }
    }

    private fun loadHistory() {
        val raw = getSharedPreferences("sciobraille", MODE_PRIVATE).getString("history", "[]").orEmpty()
        val array = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }
        historyEntries.clear()
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            historyEntries.add(
                HistoryEntry(
                    text = item.optString("text"),
                    braille = item.optString("braille"),
                    detections = item.optInt("detections"),
                    confidence = item.optDouble("confidence"),
                    createdAt = item.optLong("createdAt")
                )
            )
        }
    }

    private fun saveHistory() {
        val array = JSONArray()
        historyEntries.forEach { entry ->
            array.put(JSONObject().apply {
                put("text", entry.text)
                put("braille", entry.braille)
                put("detections", entry.detections)
                put("confidence", entry.confidence)
                put("createdAt", entry.createdAt)
            })
        }
        getSharedPreferences("sciobraille", MODE_PRIVATE).edit()
            .putString("history", array.toString())
            .apply()
    }

    private fun toggleTorch() {
        val activeCamera = camera
        if (activeCamera == null || !activeCamera.cameraInfo.hasFlashUnit()) {
            torchOn = false
            flashButton.text = "Flash"
            toast("Flash is unavailable on this device")
            return
        }
        torchOn = !torchOn
        activeCamera.cameraControl.enableTorch(torchOn)
        flashButton.text = if (torchOn) "On" else "Flash"
    }

    private fun speakOutput() {
        speakText(lastOutput)
    }

    private fun copyOutput() {
        copyText(lastOutput)
    }

    private fun shareOutput() {
        shareText(lastOutput)
    }

    private fun speakText(value: String) {
        val text = value.ifBlank { return }
        if (!isTtsReady) {
            toast("Text to speech is unavailable")
            return
        }
        runCatching {
            textToSpeech?.speak(text.replace('\n', '.'), TextToSpeech.QUEUE_FLUSH, null, "sciobraille-output")
        }.onFailure { toast("Could not read this scan") }
    }

    private fun copyText(value: String) {
        val text = value.ifBlank { return }
        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Sciobraille output", text))
        toast("Copied")
    }

    private fun shareText(value: String) {
        val text = value.ifBlank { return }
        runCatching {
            startActivity(
            Intent.createChooser(
                Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, text)
                },
                "Share scan"
            )
            )
        }.onFailure { toast("No sharing app is available") }
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_PERMISSION_REQUEST &&
            grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
        ) {
            startCamera()
        } else {
            frameOverlay.setStatus("Camera permission denied", false)
        }
    }

    override fun onDestroy() {
        stopScanning("Stopped")
        networkExecutor.shutdownNow()
        lmsAudioManager.stop()
        lmsHapticManager.stop()
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        fallbackDetector.closeIfOpened()
        super.onDestroy()
    }

    override fun onStop() {
        if (isScanning) stopScanning("Stopped")
        if (torchOn) {
            camera?.cameraControl?.enableTorch(false)
            torchOn = false
            flashButton.text = "Flash"
        }
        super.onStop()
    }

    private fun title(value: String): TextView = TextView(this).apply {
        text = value
        textSize = 34f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(ScioColors.TEXT)
        includeFontPadding = false
    }

    private fun chip(label: String): TextView = TextView(this).apply {
        text = label
        gravity = Gravity.CENTER
        textSize = 16f
        typeface = Typeface.MONOSPACE
        setTextColor(ScioColors.TEXT)
        background = rounded(ScioColors.SURFACE_CONTAINER, ScioColors.OUTLINE, 1, 18)
    }

    private fun filterChip(label: String, selected: Boolean): TextView = TextView(this).apply {
        text = label
        gravity = Gravity.CENTER
        textSize = 14f
        typeface = Typeface.MONOSPACE
        setTextColor(if (selected) Color.WHITE else ScioColors.MUTED)
        background = rounded(if (selected) ScioColors.PRIMARY_CONTAINER else ScioColors.BACKGROUND, ScioColors.OUTLINE, 1, 14)
        layoutParams = LinearLayout.LayoutParams(-2, dp(42)).apply {
            rightMargin = dp(12)
        }
        setPadding(dp(18), 0, dp(18), 0)
    }

    private fun roundControl(label: String): Button = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = 13f
        setTextColor(ScioColors.TEXT)
        background = rounded(ScioColors.SURFACE_CONTAINER, ScioColors.OUTLINE, 1, 16)
    }

    private fun actionButton(label: String, filled: Boolean, onClick: () -> Unit): Button = Button(this).apply {
        text = label
        contentDescription = label
        isAllCaps = false
        textSize = 14f
        minHeight = dp(48)
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(if (filled) Color.WHITE else ScioColors.SECONDARY)
        background = rounded(if (filled) ScioColors.SECONDARY else Color.TRANSPARENT, ScioColors.SECONDARY, 2, 6)
        setOnClickListener { onClick() }
    }

    private fun navItem(label: String, accessibilityLabel: String, onClick: () -> Unit): TextView = TextView(this).apply {
        text = label
        contentDescription = accessibilityLabel
        gravity = Gravity.CENTER
        textSize = 13f
        typeface = Typeface.MONOSPACE
        setOnClickListener { onClick() }
    }

    private fun statCard(value: String, label: String): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 8)
            addView(TextView(context).apply {
                text = value
                textSize = 22f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(ScioColors.TEXT)
                gravity = Gravity.CENTER
            })
            addView(TextView(context).apply {
                text = label
                textSize = 12f
                typeface = Typeface.MONOSPACE
                setTextColor(ScioColors.MUTED)
                gravity = Gravity.CENTER
            })
        }
    }

    private fun infoCard(title: String, items: List<String>): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(20), dp(20), dp(20), dp(20))
            addView(TextView(context).apply {
                text = title
                textSize = 22f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(ScioColors.TEXT)
            })
            items.forEach { item ->
                addView(TextView(context).apply {
                    text = item
                    textSize = 15f
                    setTextColor(ScioColors.TEXT)
                    setLineSpacing(0f, 1.35f)
                    setPadding(0, dp(14), 0, 0)
                })
            }
        }
    }

    private fun historyCard(entry: HistoryEntry): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = rounded(ScioColors.SURFACE, ScioColors.OUTLINE, 1, 10)
            setPadding(dp(20), dp(18), dp(20), dp(18))
            addView(TextView(context).apply {
                text = entry.braille.ifBlank { toBraillePreview(entry.text) }
                textSize = 20f
                letterSpacing = 0.08f
                setTextColor(ScioColors.TEXT)
            })
            addView(TextView(context).apply {
                text = entry.text
                textSize = 18f
                setTextColor(ScioColors.TEXT)
                setLineSpacing(0f, 1.35f)
                setPadding(0, dp(14), 0, dp(18))
            })
            addView(TextView(context).apply {
                val pct = (entry.confidence * 100).roundToInt()
                text = "${entry.detections} cells / $pct% / ${relativeTime(entry.createdAt)}"
                textSize = 13f
                typeface = Typeface.MONOSPACE
                setTextColor(ScioColors.MUTED)
            })
            addView(LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, dp(14), 0, 0)
                addView(actionButton("Read", false) { speakText(entry.text) }, LinearLayout.LayoutParams(0, dp(48), 1f))
                addView(actionButton("Copy", false) { copyText(entry.text) }, LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                    marginStart = dp(8)
                })
                addView(actionButton("Share", false) { shareText(entry.text) }, LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                    marginStart = dp(8)
                })
            })
        }
    }

    private fun rounded(fill: Int, stroke: Int? = null, strokeWidthDp: Int = 1, radiusDp: Int = 12): GradientDrawable {
        return GradientDrawable().apply {
            setColor(fill)
            cornerRadius = dp(radiusDp).toFloat()
            if (stroke != null) setStroke(dp(strokeWidthDp), stroke)
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).roundToInt()

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }
}

enum class AppTab {
    SCANNER,
    HISTORY,
    LEARN,
    ABOUT
}

data class HistoryEntry(
    val text: String,
    val braille: String,
    val detections: Int,
    val confidence: Double,
    val createdAt: Long
)

data class LmsLevelState(
    val level: Int,
    val title: String,
    val description: String,
    val cta: String,
    val progressPercent: Int,
    val completedLessons: Int,
    val totalLessons: Int,
    val unlocked: Boolean,
    val lockedReason: String,
    val lessons: List<LessonEntity>
)

data class LmsProgressSnapshot(
    val lessons: List<LessonEntity>,
    val progress: List<LessonProgressEntity>,
    val letterAccuracies: Map<Char, Float>,
    val streak: com.sciobraille.scanner.lms.StreakEntity?,
    val syncOverview: SyncOverview
)

data class RecognitionQuestion(
    val correctAnswer: Char,
    val options: List<Char>
)

data class ScanPracticeCell(
    val index: Int,
    val letter: Char,
    val dots: Set<Int>,
    val word: String,
    val positionInWord: Int
)

data class ScannerPayload(
    val ok: Boolean,
    val text: String,
    val stable: Boolean,
    val detections: Int,
    val confidence: Double,
    val boxes: List<DetectionBox>,
    val rawText: String = text,
    val correctedText: String = text
) {
    companion object {
        fun fromJsonOrNull(raw: String): ScannerPayload? = runCatching { fromJson(raw) }.getOrNull()

        fun fromJson(raw: String): ScannerPayload {
            val json = JSONObject(raw)
            return ScannerPayload(
                ok = json.optBoolean("ok", true),
                text = json.optString("text", ""),
                stable = json.optBoolean("stable", false),
                detections = json.optInt("detections", json.optInt("num_detections", 0)),
                confidence = json.optDouble("confidence", 0.0),
                boxes = DetectionBox.fromJsonArray(json.optJSONArray("boxes")),
                rawText = json.optString("raw_text", json.optString("text", "")),
                correctedText = json.optString("corrected_text", json.optString("text", ""))
            )
        }
    }
}

data class DetectionBox(
    val label: String,
    val confidence: Double,
    val x1: Float,
    val y1: Float,
    val x2: Float,
    val y2: Float
) {
    companion object {
        fun fromJsonArray(array: JSONArray?): List<DetectionBox> {
            if (array == null) return emptyList()
            return buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    add(
                        DetectionBox(
                            label = item.optString("label", ""),
                            confidence = item.optDouble("confidence", 0.0),
                            x1 = item.optDouble("x1", 0.0).toFloat(),
                            y1 = item.optDouble("y1", 0.0).toFloat(),
                            x2 = item.optDouble("x2", 0.0).toFloat(),
                            y2 = item.optDouble("y2", 0.0).toFloat()
                        )
                    )
                }
            }
        }
    }
}

class DetectionOverlayView(context: Context) : View(context) {
    private var boxes: List<DetectionBox> = emptyList()
    private val primaryPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.PRIMARY_CONTAINER
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }
    private val secondaryPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.SECONDARY
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 24f
        typeface = Typeface.DEFAULT_BOLD
    }
    private val labelBackgroundPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(205, 49, 48, 48)
        style = Paint.Style.FILL
    }

    fun update(newBoxes: List<DetectionBox>) {
        boxes = newBoxes
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        boxes.forEachIndexed { index, box ->
            val rect = RectF(box.x1 * width, box.y1 * height, box.x2 * width, box.y2 * height)
            val paint = if (index % 2 == 0) primaryPaint else secondaryPaint
            canvas.drawRoundRect(rect, 8f, 8f, paint)
            if (box.label.isNotBlank()) {
                val label = box.label
                val labelWidth = labelPaint.measureText(label)
                val labelTop = (rect.top - 30f).coerceAtLeast(0f)
                canvas.drawRoundRect(
                    RectF(rect.left, labelTop, rect.left + labelWidth + 14f, labelTop + 30f),
                    5f,
                    5f,
                    labelBackgroundPaint
                )
                canvas.drawText(label, rect.left + 7f, labelTop + 22f, labelPaint)
            }
        }
    }
}

class ScanFrameOverlayView(context: Context) : View(context) {
    private var scanning = false
    private var status = "Ready"
    private val framePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(140, 197, 192, 255)
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }
    private val cornerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.PRIMARY_CONTAINER
        style = Paint.Style.STROKE
        strokeWidth = 6f
    }
    private val scanPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.SECONDARY_CONTAINER
        style = Paint.Style.STROKE
        strokeWidth = 4f
    }
    private val pillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(235, 255, 219, 204)
        style = Paint.Style.FILL
    }
    private val pillStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.SECONDARY
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.SECONDARY
        textSize = 28f
        typeface = Typeface.MONOSPACE
        textAlign = Paint.Align.CENTER
    }

    fun setStatus(newStatus: String, active: Boolean) {
        status = newStatus
        scanning = active
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val inset = 28f
        val rect = RectF(inset, inset, width - inset, height - inset)
        canvas.drawRoundRect(rect, 8f, 8f, framePaint)
        val corner = 48f
        canvas.drawLine(rect.left, rect.top, rect.left + corner, rect.top, cornerPaint)
        canvas.drawLine(rect.left, rect.top, rect.left, rect.top + corner, cornerPaint)
        canvas.drawLine(rect.right, rect.top, rect.right - corner, rect.top, cornerPaint)
        canvas.drawLine(rect.right, rect.top, rect.right, rect.top + corner, cornerPaint)
        canvas.drawLine(rect.left, rect.bottom, rect.left + corner, rect.bottom, cornerPaint)
        canvas.drawLine(rect.left, rect.bottom, rect.left, rect.bottom - corner, cornerPaint)
        canvas.drawLine(rect.right, rect.bottom, rect.right - corner, rect.bottom, cornerPaint)
        canvas.drawLine(rect.right, rect.bottom, rect.right, rect.bottom - corner, cornerPaint)

        if (scanning) {
            val phase = (System.currentTimeMillis() % 1800L) / 1800f
            val y = rect.top + (rect.height() * phase)
            canvas.drawLine(rect.left + 12f, y, rect.right - 12f, y, scanPaint)
            postInvalidateDelayed(32)
        }

        val pillWidth = min(width * 0.76f, 360f)
        val pill = RectF(
            (width - pillWidth) / 2f,
            height - 76f,
            (width + pillWidth) / 2f,
            height - 28f
        )
        canvas.drawRoundRect(pill, 22f, 22f, pillPaint)
        canvas.drawRoundRect(pill, 22f, 22f, pillStrokePaint)
        canvas.drawText(status, width / 2f, pill.centerY() + 10f, textPaint)
    }
}

class SpaceView(context: Context) : View(context)

class LevelProgressView(context: Context, private val progressPercent: Int) : View(context) {
    private val trackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.SURFACE_CONTAINER
        style = Paint.Style.FILL
    }
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.PRIMARY_CONTAINER
        style = Paint.Style.FILL
    }
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ScioColors.OUTLINE
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val radius = height / 2f
        val track = RectF(0f, 0f, width.toFloat(), height.toFloat())
        canvas.drawRoundRect(track, radius, radius, trackPaint)
        val fillWidth = width * progressPercent.coerceIn(0, 100) / 100f
        if (fillWidth > 0f) {
            canvas.drawRoundRect(RectF(0f, 0f, fillWidth, height.toFloat()), radius, radius, fillPaint)
        }
        canvas.drawRoundRect(track, radius, radius, strokePaint)
    }
}

class OfflineBrailleDetector(private val context: Context) {
    private val labels = ('a'..'z').map { it.toString() }
    private val history = mutableListOf<String>()
    private var openedInterpreter: Interpreter? = null
    private val interpreter: Interpreter
        get() {
            val existing = openedInterpreter
            if (existing != null) return existing
            return Interpreter(loadModel(), Interpreter.Options().apply { setNumThreads(4) }).also {
                openedInterpreter = it
            }
        }

    fun detect(frameFile: File): ScannerPayload {
        val bitmap = BitmapFactory.decodeFile(frameFile.absolutePath)
            ?: return ScannerPayload(false, "", false, 0, 0.0, emptyList())
        val mirrorMatrix = Matrix().apply { preScale(-1f, 1f) }
        val mirrored = Bitmap.createBitmap(
            bitmap,
            0,
            0,
            bitmap.width,
            bitmap.height,
            mirrorMatrix,
            true
        )
        val scaled = Bitmap.createScaledBitmap(mirrored, FALLBACK_IMAGE_SIZE, FALLBACK_IMAGE_SIZE, true)
        val input = buildInput(scaled)
        if (scaled !== mirrored) scaled.recycle()
        if (mirrored !== bitmap) mirrored.recycle()
        bitmap.recycle()
        val outputTensor = interpreter.getOutputTensor(0)
        val outputBuffer = ByteBuffer.allocateDirect(outputTensor.numBytes()).order(ByteOrder.nativeOrder())
        interpreter.run(input, outputBuffer)
        val output = dequantizeOutput(outputBuffer)
        val shape = outputTensor.shape()
        val channels = shape[1]
        val anchors = shape[2]
        val boxes = parseDetections(output, channels, anchors)
        val rawCount = boxes.size
        val nmsBoxes = nonMaxSuppress(boxes).take(80)
        val suppressedCount = rawCount - nmsBoxes.size
        android.util.Log.d(
            "SciobrailleOffline",
            "Model: ${BuildConfig.OFFLINE_MODEL_ASSET}, Parsed: $rawCount, Suppressed: $suppressedCount, Kept: ${nmsBoxes.size}"
        )
        val displayBoxes = nmsBoxes.map { box ->
            box.copy(x1 = 1f - box.x2, x2 = 1f - box.x1)
        }
        val rawText = decodeReadingOrder(displayBoxes)
        val (stableText, stable) = stabilize(rawText)
        return ScannerPayload(
            ok = true,
            text = stableText,
            stable = stable,
            detections = nmsBoxes.size,
            confidence = nmsBoxes.map { it.confidence }.average().takeIf { !it.isNaN() } ?: 0.0,
            boxes = displayBoxes,
            rawText = rawText,
            correctedText = rawText
        )
    }

    fun closeIfOpened() {
        openedInterpreter?.close()
        openedInterpreter = null
    }

    fun resetSession() {
        history.clear()
    }

    private fun loadModel(): MappedByteBuffer {
        context.assets.openFd(BuildConfig.OFFLINE_MODEL_ASSET).use { descriptor ->
            FileInputStream(descriptor.fileDescriptor).use { input ->
                return input.channel.map(
                    FileChannel.MapMode.READ_ONLY,
                    descriptor.startOffset,
                    descriptor.declaredLength
                )
            }
        }
    }

    private fun buildInput(bitmap: Bitmap): ByteBuffer {
        val inputTensor = interpreter.getInputTensor(0)
        val buffer = ByteBuffer.allocateDirect(inputTensor.numBytes()).order(ByteOrder.nativeOrder())
        val quant = inputTensor.quantizationParams()
        val pixels = IntArray(FALLBACK_IMAGE_SIZE * FALLBACK_IMAGE_SIZE)
        bitmap.getPixels(pixels, 0, FALLBACK_IMAGE_SIZE, 0, 0, FALLBACK_IMAGE_SIZE, FALLBACK_IMAGE_SIZE)

        for (pixel in pixels) {
            putValue(buffer, inputTensor.dataType(), quant.scale, quant.zeroPoint, Color.red(pixel) / 255f)
            putValue(buffer, inputTensor.dataType(), quant.scale, quant.zeroPoint, Color.green(pixel) / 255f)
            putValue(buffer, inputTensor.dataType(), quant.scale, quant.zeroPoint, Color.blue(pixel) / 255f)
        }
        buffer.rewind()
        return buffer
    }

    private fun putValue(buffer: ByteBuffer, type: DataType, scale: Float, zeroPoint: Int, value: Float) {
        when (type) {
            DataType.FLOAT32 -> buffer.putFloat(value)
            DataType.UINT8 -> {
                val quantized = if (scale > 0f) (value / scale + zeroPoint).toInt() else (value * 255).toInt()
                buffer.put(quantized.coerceIn(0, 255).toByte())
            }
            DataType.INT8 -> {
                val quantized = if (scale > 0f) (value / scale + zeroPoint).toInt() else ((value * 255) - 128).toInt()
                buffer.put(quantized.coerceIn(-128, 127).toByte())
            }
            else -> buffer.putFloat(value)
        }
    }

    private fun dequantizeOutput(buffer: ByteBuffer): FloatArray {
        val tensor = interpreter.getOutputTensor(0)
        val type = tensor.dataType()
        val quant = tensor.quantizationParams()
        buffer.rewind()
        val values = FloatArray(tensor.numElements())
        for (index in values.indices) {
            values[index] = when (type) {
                DataType.FLOAT32 -> buffer.float
                DataType.UINT8 -> ((buffer.get().toInt() and 0xFF) - quant.zeroPoint) * quant.scale
                DataType.INT8 -> (buffer.get().toInt() - quant.zeroPoint) * quant.scale
                else -> 0f
            }
        }
        return values
    }

    private fun parseDetections(output: FloatArray, channels: Int, anchors: Int): List<DetectionBox> {
        val boxes = mutableListOf<DetectionBox>()
        for (anchor in 0 until anchors) {
            var bestScore = 0f
            var bestClass = -1
            for (classIndex in labels.indices) {
                val score = output[(4 + classIndex) * anchors + anchor]
                if (score > bestScore) {
                    bestScore = score
                    bestClass = classIndex
                }
            }
            if (bestScore < FALLBACK_CONFIDENCE || bestClass < 0 || channels < 30) continue
            var cx = output[anchor]
            var cy = output[anchors + anchor]
            var boxWidth = output[2 * anchors + anchor]
            var boxHeight = output[3 * anchors + anchor]
            if (cx > 1f || cy > 1f || boxWidth > 1f || boxHeight > 1f) {
                cx /= FALLBACK_IMAGE_SIZE
                cy /= FALLBACK_IMAGE_SIZE
                boxWidth /= FALLBACK_IMAGE_SIZE
                boxHeight /= FALLBACK_IMAGE_SIZE
            }
            val x1 = (cx - boxWidth / 2f).coerceIn(0f, 1f)
            val y1 = (cy - boxHeight / 2f).coerceIn(0f, 1f)
            val x2 = (cx + boxWidth / 2f).coerceIn(0f, 1f)
            val y2 = (cy + boxHeight / 2f).coerceIn(0f, 1f)
            if (abs(x2 - x1) <= 0.001f || abs(y2 - y1) <= 0.001f) continue
            boxes.add(DetectionBox(labels[bestClass], bestScore.toDouble(), x1, y1, x2, y2))
        }
        return boxes
    }

    private fun nonMaxSuppress(boxes: List<DetectionBox>): List<DetectionBox> {
        val selected = mutableListOf<DetectionBox>()
        val threshold = BuildConfig.DUPLICATE_IOU_THRESHOLD.toDouble()
        for (box in boxes.sortedByDescending { it.confidence }) {
            if (selected.none { iou(it, box) >= threshold }) selected.add(box)
        }
        return selected
    }

    private fun iou(a: DetectionBox, b: DetectionBox): Float {
        val left = max(a.x1, b.x1)
        val top = max(a.y1, b.y1)
        val right = min(a.x2, b.x2)
        val bottom = min(a.y2, b.y2)
        val intersection = max(0f, right - left) * max(0f, bottom - top)
        val areaA = max(0f, a.x2 - a.x1) * max(0f, a.y2 - a.y1)
        val areaB = max(0f, b.x2 - b.x1) * max(0f, b.y2 - b.y1)
        return intersection / max(0.0001f, areaA + areaB - intersection)
    }

    private fun decodeReadingOrder(boxes: List<DetectionBox>): String {
        if (boxes.isEmpty()) return ""
        val avgHeight = boxes.map { it.y2 - it.y1 }.average().toFloat()
        val eps = max(avgHeight * 0.6f, 0.01f)
        val lines = mutableListOf<MutableList<DetectionBox>>()
        for (box in boxes.sortedBy { it.centerY }) {
            val target = lines.minByOrNull { abs(median(it.map { item -> item.centerY }) - box.centerY) }
            if (target != null && abs(median(target.map { it.centerY }) - box.centerY) <= eps) {
                target.add(box)
            } else {
                lines.add(mutableListOf(box))
            }
        }
        return lines.sortedBy { median(it.map { box -> box.centerY }) }
            .joinToString("\n") { line -> decodeLine(line) }
    }

    private fun decodeLine(line: List<DetectionBox>): String {
        val sorted = line.sortedBy { it.centerX }
        if (sorted.size < 2) return sorted.joinToString("") { it.label }
        val gaps = sorted.zipWithNext { left, right -> right.centerX - left.centerX }
        val medianGap = median(gaps)
        val compactGaps = gaps.filter { it <= medianGap * 1.25f }
        val cellGap = median(compactGaps.takeIf { it.isNotEmpty() } ?: gaps)
        val medianWidth = median(sorted.map { it.x2 - it.x1 })
        val spaceThreshold = max(
            cellGap * FALLBACK_SPACE_GAP_MULTIPLIER.toFloat(),
            medianWidth * FALLBACK_SPACE_WIDTH_MULTIPLIER.toFloat()
        )
        return buildString {
            append(sorted.first().label)
            sorted.drop(1).forEachIndexed { index, box ->
                if (gaps[index] > spaceThreshold) append(' ')
                append(box.label)
            }
        }
    }

    private fun stabilize(text: String): Pair<String, Boolean> {
        if (text.isNotBlank()) {
            val previous = history.groupingBy { it }.eachCount().maxByOrNull { it.value }?.key
            if (!previous.isNullOrBlank() && textOverlapRatio(text, previous) < 0.3) history.clear()
            history.add(text)
            while (history.size > FALLBACK_HISTORY_SIZE) history.removeAt(0)
        }
        if (history.isEmpty()) return text to false
        val winner = history.groupingBy { it }.eachCount().maxByOrNull { it.value }
        return (winner?.key ?: text) to ((winner?.value ?: 0) >= 2)
    }

    private fun textOverlapRatio(left: String, right: String): Double {
        val a = left.lowercase(Locale.US).filter { it.isLetterOrDigit() }
        val b = right.lowercase(Locale.US).filter { it.isLetterOrDigit() }
        if (a.isEmpty() || b.isEmpty()) return 0.0
        val previous = IntArray(b.length + 1) { it }
        a.forEachIndexed { leftIndex, leftChar ->
            var diagonal = previous[0]
            previous[0] = leftIndex + 1
            b.forEachIndexed { rightIndex, rightChar ->
                val old = previous[rightIndex + 1]
                previous[rightIndex + 1] = min(
                    min(previous[rightIndex + 1] + 1, previous[rightIndex] + 1),
                    diagonal + if (leftChar == rightChar) 0 else 1
                )
                diagonal = old
            }
        }
        return 1.0 - previous[b.length].toDouble() / max(a.length, b.length).toDouble()
    }

    private fun median(values: List<Float>): Float {
        if (values.isEmpty()) return 0f
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 0) {
            (sorted[middle - 1] + sorted[middle]) / 2f
        } else {
            sorted[middle]
        }
    }
}

private val DetectionBox.centerX: Float get() = (x1 + x2) / 2f
private val DetectionBox.centerY: Float get() = (y1 + y2) / 2f

private fun relativeTime(timestamp: Long): String {
    val minutes = ((System.currentTimeMillis() - timestamp) / 60000L).coerceAtLeast(0L)
    return when {
        minutes < 1 -> "now"
        minutes < 60 -> "${minutes}m ago"
        minutes < 1440 -> "${minutes / 60}h ago"
        else -> "${minutes / 1440}d ago"
    }
}

private fun toBraillePreview(text: String): String {
    return text.lowercase(Locale.US)
        .asSequence()
        .filter { it == ' ' || it in 'a'..'z' || it == '\n' }
        .map { char ->
            when (char) {
                ' ' -> ' '
                '\n' -> '\n'
                else -> brailleChar(char)
            }
        }
        .joinToString("")
        .take(120)
}

private fun brailleChar(char: Char): Char {
    val masks = mapOf(
        'a' to 0b000001,
        'b' to 0b000011,
        'c' to 0b001001,
        'd' to 0b011001,
        'e' to 0b010001,
        'f' to 0b001011,
        'g' to 0b011011,
        'h' to 0b010011,
        'i' to 0b001010,
        'j' to 0b011010,
        'k' to 0b000101,
        'l' to 0b000111,
        'm' to 0b001101,
        'n' to 0b011101,
        'o' to 0b010101,
        'p' to 0b001111,
        'q' to 0b011111,
        'r' to 0b010111,
        's' to 0b001110,
        't' to 0b011110,
        'u' to 0b100101,
        'v' to 0b100111,
        'w' to 0b111010,
        'x' to 0b101101,
        'y' to 0b111101,
        'z' to 0b110101
    )
    return (0x2800 + (masks[char] ?: 0)).toChar()
}
