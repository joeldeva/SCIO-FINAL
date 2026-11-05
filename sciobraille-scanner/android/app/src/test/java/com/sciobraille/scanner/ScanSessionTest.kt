package com.sciobraille.scanner
import org.junit.Assert.*
import org.junit.Test
class ScanSessionTest {
 @Test fun twoFramesRequiredAndDuplicatesSuppressed() { val s=ScanSession(); assertFalse(s.accept("ab").stable); assertTrue(s.accept("ab").isNew); assertFalse(s.accept("ab").isNew) }
 @Test fun blankClearsStability() { val s=ScanSession(); s.accept("a"); s.accept("a"); assertFalse(s.accept("").stable); assertFalse(s.accept("b").stable) }
 @Test fun photoCanBeSavedWithoutClaimingStability() { val r=ScanSession().accept("a",true); assertTrue(r.isNew); assertFalse(r.stable) }
 @Test fun resetAllowsSameDocumentAgain() { val s=ScanSession();s.accept("a",true);s.reset();assertTrue(s.accept("a",true).isNew) }
}
