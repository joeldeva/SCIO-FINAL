package com.sciobraille.scanner

import kotlin.math.abs
import kotlin.math.max

object ConfidenceThresholds {
    const val HIGH = 0.80
    const val MEDIUM = 0.55
}

enum class ConfidenceBand { HIGH, MEDIUM, LOW }

fun confidenceBand(confidence: Double): ConfidenceBand = when {
    confidence >= ConfidenceThresholds.HIGH -> ConfidenceBand.HIGH
    confidence >= ConfidenceThresholds.MEDIUM -> ConfidenceBand.MEDIUM
    else -> ConfidenceBand.LOW
}

enum class ScanOrientation { NORMAL, FLIPPED }
enum class RecognitionMode { ONLINE, OFFLINE, UNKNOWN }

data class RecognitionCell(
    val character: String,
    val confidence: Double,
    val box: DetectionBox,
    val lineNumber: Int,
    val characterIndex: Int,
    val wordIndex: Int
) {
    val confidenceBand: ConfidenceBand = confidenceBand(confidence)
}

object RecognitionMetadataAssembler {
    fun fromBoxes(boxes: List<DetectionBox>): List<RecognitionCell> {
        if (boxes.isEmpty()) return emptyList()
        val aligned = alignedCenters(boxes)
        fun y(box: DetectionBox) = aligned.getValue(box)
        val averageHeight = boxes.map { it.y2 - it.y1 }.average().toFloat()
        val epsilon = max(averageHeight * 0.6f, 0.01f)
        val lines = mutableListOf<MutableList<DetectionBox>>()
        boxes.sortedBy { y(it) }.forEach { box ->
            val target = lines.minByOrNull { line -> abs(median(line.map { y(it) }) - y(box)) }
            if (target != null && abs(median(target.map { y(it) }) - y(box)) <= epsilon) {
                target += box
            } else {
                lines += mutableListOf(box)
            }
        }

        return buildList {
            lines.sortedBy { median(it.map { box -> y(box) }) }
                .forEachIndexed { lineIndex, line ->
                    val sorted = line.sortedBy { it.centerXValue }
                    val wordBreaks = wordBreaks(sorted)
                    var wordIndex = 0
                    sorted.forEachIndexed { characterIndex, box ->
                        if (characterIndex > 0 && wordBreaks.getOrElse(characterIndex - 1) { false }) wordIndex += 1
                        add(
                            RecognitionCell(
                                character = box.label,
                                confidence = box.confidence,
                                box = box,
                                lineNumber = lineIndex,
                                characterIndex = characterIndex,
                                wordIndex = wordIndex
                            )
                        )
                    }
                }
        }
    }

    fun displayText(cells: List<RecognitionCell>, maskLowConfidence: Boolean): String {
        if (cells.isEmpty()) return ""
        return cells.groupBy { it.lineNumber }.toSortedMap().values.joinToString("\n") { line ->
            val sorted = line.sortedBy { it.characterIndex }
            buildString {
                var previousWord = sorted.firstOrNull()?.wordIndex ?: 0
                sorted.forEachIndexed { index, cell ->
                    if (index > 0 && cell.wordIndex != previousWord) append(' ')
                    append(if (maskLowConfidence && cell.confidenceBand == ConfidenceBand.LOW) "?" else cell.character)
                    previousWord = cell.wordIndex
                }
            }
        }
    }

    private fun alignedCenters(boxes: List<DetectionBox>): Map<DetectionBox, Float> {
        val height=median(boxes.map { it.y2-it.y1 })
        if(boxes.size<4 || height<=0) return boxes.associateWith { it.centerYValue }
        val slopes=boxes.mapNotNull { left ->
            boxes.mapNotNull { right ->
                val dx=right.centerXValue-left.centerXValue
                val dy=right.centerYValue-left.centerYValue
                if(dx>height*.35f && dx<height*3f && abs(dy/dx)<=.36f) dx to dy/dx else null
            }.minByOrNull { it.first }?.second
        }
        val slope=median(slopes)
        val accepted=slopes.size>=3 && abs(slope)>=.03f && median(slopes.map { abs(it-slope) })<=.08f
        return boxes.associateWith { it.centerYValue - (if(accepted) slope*it.centerXValue else 0f) }
    }

    private fun wordBreaks(sorted: List<DetectionBox>): List<Boolean> {
        if (sorted.size < 2) return emptyList()
        val gaps = sorted.zipWithNext { left, right -> right.centerXValue - left.centerXValue }
        val medianGap = median(gaps)
        val compact = gaps.filter { it <= medianGap * 1.25f }
        val cellGap = median(compact.ifEmpty { gaps })
        val medianWidth = median(sorted.map { it.x2 - it.x1 })
        val threshold = max(cellGap * 1.8f, medianWidth * 1.35f)
        return gaps.map { it > threshold }
    }

    private fun median(values: List<Float>): Float {
        if (values.isEmpty()) return 0f
        val sorted = values.sorted()
        val middle = sorted.size / 2
        return if (sorted.size % 2 == 0) (sorted[middle - 1] + sorted[middle]) / 2f else sorted[middle]
    }
}

private val DetectionBox.centerXValue: Float get() = (x1 + x2) / 2f
private val DetectionBox.centerYValue: Float get() = (y1 + y2) / 2f
