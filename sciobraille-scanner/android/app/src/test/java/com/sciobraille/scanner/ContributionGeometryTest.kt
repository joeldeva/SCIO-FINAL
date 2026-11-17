package com.sciobraille.scanner

import org.junit.Assert.assertEquals
import org.junit.Test

class ContributionGeometryTest {
    private val box = DetectionBox(
        label = "h",
        confidence = 0.9,
        x1 = 0.1f,
        y1 = 0.2f,
        x2 = 0.3f,
        y2 = 0.4f
    )

    @Test
    fun naturalInputKeepsCoordinates() {
        assertEquals(listOf(box), ContributionGeometry.modelFacingBoxes(listOf(box), mirrored = false))
    }

    @Test
    fun mirroredInputMapsDisplayBoxToExportedImage() {
        val result = ContributionGeometry.modelFacingBoxes(listOf(box), mirrored = true).single()

        assertEquals(0.7f, result.x1, 0.0001f)
        assertEquals(0.9f, result.x2, 0.0001f)
        assertEquals(box.y1, result.y1)
        assertEquals(box.y2, result.y2)
        assertEquals("h", result.label)
    }
}
