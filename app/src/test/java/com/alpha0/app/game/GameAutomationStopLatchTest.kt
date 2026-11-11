package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GameAutomationStopLatchTest {
    @Test fun stopLatchesAcrossRepeatedReadersAndSameCaptureCannotReset() {
        val latch = GameAutomationStopLatch()
        assertFalse(latch.state.value.latched)
        latch.stop("capture-A")
        val reader = latch.state
        assertTrue(reader.value.latched)
        assertEquals("capture-A", reader.value.stoppedCaptureId)
        assertFalse(latch.canResetForNewCapture("capture-A"))
        assertFalse(latch.resetForNewCapture("capture-A"))
        assertFalse(latch.resetForNewCapture(null))
        assertTrue(reader.value.latched)
    }

    @Test fun explicitNewCaptureResetIsNotAutomatic() {
        val latch = GameAutomationStopLatch()
        latch.stop("capture-A")
        assertTrue(latch.canResetForNewCapture("capture-B"))
        assertTrue(latch.state.value.latched) // still stopped until explicit reset
        assertTrue(latch.resetForNewCapture("capture-B"))
        assertFalse(latch.state.value.latched)
        latch.stop("capture-B")
        assertFalse(latch.resetForNewCapture("capture-B"))
        assertTrue(latch.state.value.latched)
    }

    @Test fun stoppingWithoutAVisibleCaptureStillRequiresFreshCapture() {
        val latch = GameAutomationStopLatch()
        latch.stop(null)
        latch.stop("")
        assertTrue(latch.state.value.latched)
        assertFalse(latch.resetForNewCapture(null))
        assertFalse(latch.resetForNewCapture(""))
        assertTrue(latch.resetForNewCapture("capture-new"))
        assertFalse(latch.state.value.latched)
    }

    @Test fun lostCaptureIdDoesNotEraseKnownStoppedGeneration() {
        val latch = GameAutomationStopLatch()
        latch.stop("capture-A")
        latch.stop(null)
        assertEquals("capture-A", latch.state.value.stoppedCaptureId)
        assertFalse(latch.resetForNewCapture("capture-A"))
    }

    @Test fun independentInstancesDoNotCrossAuthorize() {
        val first = GameAutomationStopLatch()
        val second = GameAutomationStopLatch()
        first.stop("capture-A")
        assertTrue(first.state.value.latched)
        assertFalse(second.state.value.latched)
        assertFalse(first.resetForNewCapture("capture-A"))
    }
}
