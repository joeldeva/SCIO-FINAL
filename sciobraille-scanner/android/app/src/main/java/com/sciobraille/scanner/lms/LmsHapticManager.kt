package com.sciobraille.scanner.lms

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

class LmsHapticManager(
    private val context: Context
) {
    fun dot(dot: Int) {
        val pattern = when (dot) {
            1 -> longArrayOf(0, SHORT)
            2 -> longArrayOf(0, SHORT, GAP_SHORT, SHORT)
            3 -> longArrayOf(0, SHORT, GAP_SHORT, SHORT, GAP_SHORT, SHORT)
            4 -> longArrayOf(0, LONG)
            5 -> longArrayOf(0, LONG, GAP_LONG, LONG)
            6 -> longArrayOf(0, LONG, GAP_LONG, LONG, GAP_LONG, LONG)
            else -> return
        }
        vibrate(pattern)
    }

    fun success() {
        vibrate(longArrayOf(0, SHORT, GAP_SHORT, SHORT, GAP_SHORT, LONG))
    }

    fun error() {
        vibrate(longArrayOf(0, LONG, GAP_SHORT, SHORT))
    }

    fun completion() {
        vibrate(longArrayOf(0, MEDIUM, GAP_MEDIUM, MEDIUM, GAP_MEDIUM, MEDIUM))
    }

    fun stop() {
        runCatching { vibrator()?.cancel() }
    }

    private fun vibrate(pattern: LongArray) {
        runCatching {
            val vibrator = vibrator() ?: return
            if (!vibrator.hasVibrator()) return
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(pattern, -1)
            }
        }
    }

    private fun vibrator(): Vibrator? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)
                ?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
    }

    private companion object {
        const val SHORT = 55L
        const val LONG = 210L
        const val MEDIUM = 125L
        const val GAP_SHORT = 70L
        const val GAP_LONG = 120L
        const val GAP_MEDIUM = 100L
    }
}
