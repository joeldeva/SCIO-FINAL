package com.sciobraille.scanner

import org.junit.Assert.assertEquals
import org.junit.Test

class LetterboxGeometryTest {
    @Test
    fun wideImagePreservesAspectRatioAndRemovesVerticalPadding() {
        val geometry = LetterboxGeometry.calculate(1600, 654)

        assertEquals(640, geometry.scaledWidth)
        assertEquals(262, geometry.scaledHeight)
        assertEquals(0, geometry.padX)
        assertEquals(189, geometry.padY)
        assertEquals(0f, geometry.originalNormalizedX(0f), 0.0001f)
        assertEquals(1f, geometry.originalNormalizedX(1f), 0.0001f)
        assertEquals(0f, geometry.originalNormalizedY(189f / 640f), 0.002f)
        assertEquals(1f, geometry.originalNormalizedY(451f / 640f), 0.002f)
    }

    @Test
    fun portraitImagePreservesAspectRatioAndRemovesHorizontalPadding() {
        val geometry = LetterboxGeometry.calculate(654, 1600)

        assertEquals(262, geometry.scaledWidth)
        assertEquals(640, geometry.scaledHeight)
        assertEquals(189, geometry.padX)
        assertEquals(0, geometry.padY)
    }
}
