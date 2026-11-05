package com.sciobraille.scanner
import org.junit.Assert.assertEquals
import org.junit.Test
class ReadingOrderTest {
 private fun cell(letter:String,x:Float,y:Float)=DetectionBox(letter,.9,x,y,x+.025f,y+.06f)
 @Test fun skewedRowsHaveCorrectOrder() {
  val boxes=(0..5).flatMap { i -> val x=.05f+i*.06f;listOf(cell(('a'+i).toString(),x,.1f+x*.25f),cell(('g'+i).toString(),x,.3f+x*.25f)) }.reversed()
  assertEquals("abcdef\nghijkl",RecognitionMetadataAssembler.displayText(RecognitionMetadataAssembler.fromBoxes(boxes),false))
 }
 @Test fun wordGapsAndUncertainCellsArePreserved() {
  val boxes=listOf(cell("a",.1f,.1f),cell("b",.16f,.1f),cell("c",.22f,.1f),cell("d",.4f,.1f).copy(confidence=.3))
  assertEquals("abc ?",RecognitionMetadataAssembler.displayText(RecognitionMetadataAssembler.fromBoxes(boxes),true))
 }
}
