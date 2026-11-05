package com.sciobraille.scanner

/** Stability requires two consecutive frames. One-shot capture is never marked stable. */
class ScanSession {
    private var previous = ""
    private var repeats = 0
    private var published = ""
    data class Reading(val text: String, val stable: Boolean, val isNew: Boolean)
    fun accept(text: String, oneShot: Boolean = false): Reading {
        val clean = text.trim()
        if (clean.isEmpty()) { previous = ""; repeats = 0; return Reading("", false, false) }
        repeats = if (clean == previous) repeats + 1 else 1
        previous = clean
        val stable = repeats >= 2
        val fresh = (stable || oneShot) && clean != published
        if (fresh) published = clean
        return Reading(clean, stable, fresh)
    }
    fun reset() { previous = ""; repeats = 0; published = "" }
}
