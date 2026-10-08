package com.sciobraille.scanner

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.atan

object ScanQualityConfig {
    const val DARK_LUMINANCE = 55.0
    const val BRIGHT_LUMINANCE = 220.0
    const val CLIPPED_RATIO = 0.35
    const val MIN_SHARPNESS = 14.0
    const val MIN_BOX_WIDTH = 0.025f
    const val MAX_BOX_WIDTH = 0.22f
    const val MIN_REGION_AREA = 0.018f
    const val MAX_TILT_DEGREES = 8.0
    const val LOW_AVERAGE_CONFIDENCE = 0.55
    const val VERY_FEW_CELLS = 2
}

data class FrameQualityMetrics(
    val meanLuminance: Double,
    val darkPixelRatio: Double,
    val brightPixelRatio: Double,
    val sharpness: Double
)

enum class BrightnessState { GOOD, TOO_DARK, TOO_BRIGHT }
enum class BlurState { SHARP, BLURRED }
enum class DistanceState { GOOD, TOO_FAR, TOO_CLOSE, UNKNOWN }
enum class TiltState { GOOD, TILTED, UNKNOWN }
enum class DetectionState { GOOD, NONE, VERY_FEW, LOW_CONFIDENCE }

data class ScanQualityResult(
    val qualityScore: Int,
    val brightnessState: BrightnessState,
    val blurState: BlurState,
    val distanceState: DistanceState,
    val tiltState: TiltState,
    val detectionState: DetectionState,
    val recommendedAction: String?
)

object ScanQualityAnalyzer {
    fun analyze(
        frame: FrameQualityMetrics?,
        cells: List<RecognitionCell>,
        orientation: ScanOrientation
    ): ScanQualityResult {
        val brightness = when {
            frame == null -> BrightnessState.GOOD
            frame.meanLuminance < ScanQualityConfig.DARK_LUMINANCE ||
                frame.darkPixelRatio > ScanQualityConfig.CLIPPED_RATIO -> BrightnessState.TOO_DARK
            frame.meanLuminance > ScanQualityConfig.BRIGHT_LUMINANCE ||
                frame.brightPixelRatio > ScanQualityConfig.CLIPPED_RATIO -> BrightnessState.TOO_BRIGHT
            else -> BrightnessState.GOOD
        }
        val blur = if (frame != null && frame.sharpness < ScanQualityConfig.MIN_SHARPNESS) {
            BlurState.BLURRED
        } else BlurState.SHARP
        val distance = distanceState(cells)
        val tilt = tiltState(cells)
        val averageConfidence = cells.map { it.confidence }.average().takeIf { !it.isNaN() } ?: 0.0
        val detection = when {
            cells.isEmpty() -> DetectionState.NONE
            cells.size <= ScanQualityConfig.VERY_FEW_CELLS -> DetectionState.VERY_FEW
            averageConfidence < ScanQualityConfig.LOW_AVERAGE_CONFIDENCE -> DetectionState.LOW_CONFIDENCE
            else -> DetectionState.GOOD
        }
        val recommendation = when {
            detection == DetectionState.NONE -> "No Braille detected. Align the page inside the frame."
            brightness == BrightnessState.TOO_DARK -> "Lighting is too low. Turn on the flash or move to a brighter area."
            brightness == BrightnessState.TOO_BRIGHT -> "Image is overexposed. Reduce direct light and scan again."
            blur == BlurState.BLURRED -> "Image is blurred. Hold the phone steady and scan again."
            distance == DistanceState.TOO_FAR -> "Move closer and scan again."
            distance == DistanceState.TOO_CLOSE -> "Move farther away so the Braille cells fit inside the frame."
            detection == DetectionState.VERY_FEW -> "Very few Braille cells were detected. Align the full Braille region and rescan."
            detection == DetectionState.LOW_CONFIDENCE -> "Some cells have low confidence. Hold steady and rescan."
            tilt == TiltState.TILTED -> "Page is tilted. Align the Braille lines horizontally."
            orientation == ScanOrientation.FLIPPED -> "Reverse-side Braille detected. Flipped orientation was used."
            else -> null
        }
        var score = 100
        if (brightness != BrightnessState.GOOD) score -= 20
        if (blur != BlurState.SHARP) score -= 20
        if (distance != DistanceState.GOOD && distance != DistanceState.UNKNOWN) score -= 15
        if (tilt == TiltState.TILTED) score -= 10
        score -= when (detection) {
            DetectionState.NONE -> 45
            DetectionState.VERY_FEW -> 25
            DetectionState.LOW_CONFIDENCE -> 20
            DetectionState.GOOD -> 0
        }
        return ScanQualityResult(score.coerceIn(0, 100), brightness, blur, distance, tilt, detection, recommendation)
    }

    private fun distanceState(cells: List<RecognitionCell>): DistanceState {
        if (cells.isEmpty()) return DistanceState.UNKNOWN
        val averageWidth = cells.map { it.box.x2 - it.box.x1 }.average().toFloat()
        val minX = cells.minOf { it.box.x1 }
        val maxX = cells.maxOf { it.box.x2 }
        val minY = cells.minOf { it.box.y1 }
        val maxY = cells.maxOf { it.box.y2 }
        val regionArea = (maxX - minX).coerceAtLeast(0f) * (maxY - minY).coerceAtLeast(0f)
        return when {
            averageWidth < ScanQualityConfig.MIN_BOX_WIDTH || regionArea < ScanQualityConfig.MIN_REGION_AREA -> DistanceState.TOO_FAR
            averageWidth > ScanQualityConfig.MAX_BOX_WIDTH -> DistanceState.TOO_CLOSE
            else -> DistanceState.GOOD
        }
    }

    private fun tiltState(cells: List<RecognitionCell>): TiltState {
        val line = cells.groupBy { it.lineNumber }.maxByOrNull { it.value.size }?.value.orEmpty()
        if (line.size < 3) return TiltState.UNKNOWN
        val xs = line.map { (it.box.x1 + it.box.x2) / 2.0 }
        val ys = line.map { (it.box.y1 + it.box.y2) / 2.0 }
        val meanX = xs.average()
        val meanY = ys.average()
        val denominator = xs.sumOf { (it - meanX) * (it - meanX) }
        if (denominator <= 0.000001) return TiltState.UNKNOWN
        val slope = xs.indices.sumOf { (xs[it] - meanX) * (ys[it] - meanY) } / denominator
        val degrees = abs(atan(slope) * 180.0 / PI)
        return if (degrees > ScanQualityConfig.MAX_TILT_DEGREES) TiltState.TILTED else TiltState.GOOD
    }
}
