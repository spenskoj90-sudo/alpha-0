package com.alpha0.app.game

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GameAutomationCaptureGuardTest {
    private fun observed(id: String = "capture-A") = ObservationSnapshot(
        status = ObservationStatus.OBSERVING, captureId = id,
        frames = 1, lastFrameAt = 120,
    )

    @Test fun `source hidden revokes already-observed generation and visible return cannot reset Stop`() {
        val latch = GameAutomationStopLatch()
        val current = observed()
        GameAutomationCaptureGuard.onVisibilityChanged(current, "capture-A", true, latch)
        assertFalse(latch.state.value.latched)
        GameAutomationCaptureGuard.onVisibilityChanged(current, "capture-A", false, latch)
        assertTrue(latch.state.value.latched)
        GameAutomationCaptureGuard.onVisibilityChanged(current, "capture-A", true, latch)
        assertFalse(latch.resetForNewCapture("capture-A"))
        latch.onCaptureStarted("capture-A")
        assertFalse(latch.resetForNewCapture("capture-A"))
        latch.onCaptureStarted("capture-B")
        assertTrue(latch.resetForNewCapture("capture-B"))
    }

    @Test fun `first setup events and stale capture callbacks cannot latch unrelated generation`() {
        val latch = GameAutomationStopLatch()
        val waiting = ObservationSnapshot(status = ObservationStatus.WAITING, captureId = "capture-A")
        GameAutomationCaptureGuard.onVisibilityChanged(waiting, "capture-A", false, latch)
        GameAutomationCaptureGuard.onGeometryChanged(waiting, "capture-A", latch)
        GameAutomationCaptureGuard.onGeometryChanged(observed().copy(frames = 0), "capture-A", latch)
        GameAutomationCaptureGuard.onVisibilityChanged(observed(), "capture-old", false, latch)
        GameAutomationCaptureGuard.onGeometryChanged(observed(), "capture-old", latch)
        GameAutomationCaptureGuard.onVisibilityChanged(
            observed().copy(status = ObservationStatus.STOPPED), "capture-A", false, latch,
        )
        assertFalse(latch.state.value.latched)
    }

    @Test fun `resize after first observed frame disarms without discarding observation session`() {
        val latch = GameAutomationStopLatch()
        val current = observed()
        GameAutomationCaptureGuard.onGeometryChanged(current, "capture-A", latch)
        assertTrue(latch.state.value.latched)
        assertFalse(latch.resetForNewCapture("capture-A"))
        assertTrue(current.status == ObservationStatus.OBSERVING)
        assertTrue(current.frames == 1L)
    }
}
