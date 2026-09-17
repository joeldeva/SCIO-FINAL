package com.sciobraille.scanner.lms

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import kotlin.math.roundToInt

class BrailleCellView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : LinearLayout(context, attrs, defStyleAttr) {
    var activeDots: Set<Int> = emptySet()
        set(value) {
            field = value.filterValidDots()
            renderDots()
        }

    var visitedDots: Set<Int> = emptySet()
        set(value) {
            field = value.filterValidDots()
            renderDots()
        }

    var showDotNumbers: Boolean = true
        set(value) {
            field = value
            renderDots()
        }

    var interactive: Boolean = true
        set(value) {
            field = value
            renderDots()
        }

    var onDotClick: ((dotNumber: Int) -> Unit)? = null

    private val dotViews = mutableMapOf<Int, TextView>()

    init {
        orientation = HORIZONTAL
        gravity = Gravity.CENTER
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = rounded(DARK_CARD, DARK_BORDER, 1, 20)
        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        buildGrid()
        renderDots()
    }

    fun setDots(
        activeDots: Set<Int>,
        visitedDots: Set<Int> = this.visitedDots,
        showDotNumbers: Boolean = this.showDotNumbers,
        interactive: Boolean = this.interactive
    ) {
        this.activeDots = activeDots
        this.visitedDots = visitedDots
        this.showDotNumbers = showDotNumbers
        this.interactive = interactive
        renderDots()
    }

    private fun buildGrid() {
        removeAllViews()
        dotViews.clear()

        val leftColumn = dotColumn()
        val rightColumn = dotColumn()
        addView(leftColumn, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        addView(rightColumn, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))

        listOf(1, 2, 3).forEach { dot ->
            leftColumn.addView(dotView(dot), dotLayoutParams())
        }
        listOf(4, 5, 6).forEach { dot ->
            rightColumn.addView(dotView(dot), dotLayoutParams())
        }
    }

    private fun dotColumn(): LinearLayout {
        return LinearLayout(context).apply {
            orientation = VERTICAL
            gravity = Gravity.CENTER
        }
    }

    private fun dotView(dot: Int): TextView {
        return TextView(context).apply {
            gravity = Gravity.CENTER
            typeface = Typeface.DEFAULT_BOLD
            textSize = 20f
            minWidth = dp(88)
            minHeight = dp(88)
            isClickable = true
            isFocusable = true
            setOnClickListener {
                if (interactive) onDotClick?.invoke(dot)
            }
        }.also { dotViews[dot] = it }
    }

    private fun dotLayoutParams(): LayoutParams {
        return LayoutParams(dp(92), dp(92)).apply {
            topMargin = dp(8)
            bottomMargin = dp(8)
            leftMargin = dp(8)
            rightMargin = dp(8)
        }
    }

    private fun renderDots() {
        importantForAccessibility = if (interactive) {
            View.IMPORTANT_FOR_ACCESSIBILITY_NO
        } else {
            View.IMPORTANT_FOR_ACCESSIBILITY_YES
        }
        val activeDescription = if (activeDots.isEmpty()) {
            "no active dots"
        } else {
            activeDots.sorted().joinToString(prefix = "dots ", separator = ", ")
        }
        contentDescription = "Braille cell with $activeDescription."
        dotViews.forEach { (dot, view) ->
            val active = dot in activeDots
            val visited = dot in visitedDots
            view.text = dotLabel(dot, active, visited)
            view.textSize = when {
                showDotNumbers && (active || visited) -> 17f
                showDotNumbers -> 22f
                else -> 24f
            }
            view.setTextColor(if (active) Color.WHITE else DARK_TEXT)
            view.background = rounded(
                fill = when {
                    active -> ACTIVE_FILL
                    visited -> VISITED_FILL
                    else -> INACTIVE_FILL
                },
                stroke = when {
                    active -> ACTIVE_STROKE
                    visited -> VISITED_STROKE
                    else -> INACTIVE_STROKE
                },
                strokeWidthDp = if (active || visited) 4 else 2,
                radiusDp = 46
            )
            view.alpha = if (interactive) 1f else 0.72f
            view.isEnabled = interactive
            view.isClickable = interactive
            view.isFocusable = interactive
            view.importantForAccessibility = if (interactive) {
                View.IMPORTANT_FOR_ACCESSIBILITY_YES
            } else {
                View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }
            view.contentDescription = dotContentDescription(dot, active, visited)
            view.elevation = dp(if (active) 8 else if (visited) 4 else 0).toFloat()
        }
    }

    private fun dotLabel(dot: Int, active: Boolean, visited: Boolean): String {
        return when {
            showDotNumbers && active -> "$dot\nOn"
            showDotNumbers && visited -> "$dot\nSeen"
            showDotNumbers -> dot.toString()
            active -> "On"
            visited -> "Seen"
            else -> "Off"
        }
    }

    private fun dotContentDescription(dot: Int, active: Boolean, visited: Boolean): String {
        val state = when {
            active -> "active"
            visited -> "visited"
            else -> "inactive"
        }
        return "Dot $dot, ${BrailleMappings.getDotPositionDescription(dot)}, $state"
    }

    private fun rounded(fill: Int, stroke: Int?, strokeWidthDp: Int, radiusDp: Int): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(fill)
            cornerRadius = dp(radiusDp).toFloat()
            if (stroke != null) setStroke(dp(strokeWidthDp), stroke)
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).roundToInt()
    }

    private fun Set<Int>.filterValidDots(): Set<Int> {
        return filter { it in 1..6 }.toSet()
    }

    companion object {
        private const val DARK_CARD = 0xFF151720.toInt()
        private const val DARK_BORDER = 0xFF5C6075.toInt()
        private const val DARK_TEXT = 0xFFECEAF6.toInt()
        private const val ACTIVE_FILL = 0xFF7169D4.toInt()
        private const val ACTIVE_STROKE = 0xFFFFDBCC.toInt()
        private const val VISITED_FILL = 0xFF2D3040.toInt()
        private const val VISITED_STROKE = 0xFFB9B4FF.toInt()
        private const val INACTIVE_FILL = 0xFF232631.toInt()
        private const val INACTIVE_STROKE = 0xFF8D91AA.toInt()
    }
}
