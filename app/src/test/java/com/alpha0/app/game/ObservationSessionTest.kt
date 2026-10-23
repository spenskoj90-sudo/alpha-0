package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class ObservationSessionTest {
    @Test fun `frames require an active visible session`() {
        val session = ObservationSession()
        assertFalse(session.frame("a", 10))
        session.start("a", 100)
        assertEquals("a", session.snapshot.captureId)
        assertFalse(session.frame("a", 101))
        session.visibility("a", true, 102)
        assertTrue(session.frame("a", 103))
        assertEquals(1L, session.snapshot.frames)
    }

    @Test fun `stop clears observations and rejects late work`() {
        val session = visibleSession()
        session.frame("a", 110)
        assertTrue(session.recognized("a", 1, 110, 120, HealthCandidate(4, 20, 0)))
        session.stop("USER_STOP")
        assertNull(session.snapshot.health)
        assertFalse(session.frame("a", 121))
        assertFalse(session.recognized("a", 1, 110, 122, HealthCandidate(4, 20, 0)))
        assertEquals(ObservationStatus.STOPPED, session.snapshot.status)
        assertNull(session.snapshot.captureId)
    }

    @Test fun `hidden content removes health without pretending it is healthy`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.recognized("a", 1, 110, 120, HealthCandidate(4, 20, 0))
        session.visibility("a", false, 130)
        assertNull(session.snapshot.health)
        assertEquals(ObservationStatus.PAUSED, session.snapshot.status)
        assertFalse(session.frame("a", 140))
    }

    @Test fun `prior session callbacks cannot alter a replacement session`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.start("b", 200)
        session.visibility("b", true, 201)
        session.visibility("a", false, 202)
        assertFalse(session.recognized("a", 1, 110, 203, HealthCandidate(4, 20, 0)))
        assertTrue(session.frame("b", 204))
        assertEquals(ObservationStatus.OBSERVING, session.snapshot.status)
        assertNull(session.snapshot.health)
    }

    @Test fun `only the latest fresh frame can contribute health`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.frame("a", 120)
        assertFalse(session.recognized("a", 1, 110, 130, HealthCandidate(4, 20, 0)))
        assertFalse(session.recognized("a", 2, 119, 130, HealthCandidate(4, 20, 0)))
        assertFalse(session.recognized("a", 2, 120, 5121, HealthCandidate(4, 20, 0)))
        assertNull(session.snapshot.health)
        assertTrue(session.recognized("a", 2, 120, 130, HealthCandidate(4, 20, 0)))
        session.tick(5130)
        assertNull(session.snapshot.health)
    }

    @Test fun `OCR timing distinguishes capture processing from manual Save and misses`() {
        val session = visibleSession()
        assertTrue(session.frame("a", 110))
        assertTrue(session.recognized("a", 1, 110, 125, HealthCandidate(13, 20, 0)))
        assertEquals(125L, session.snapshot.lastCompletedOcrAt)
        assertEquals(15L, session.snapshot.lastOcrLatencyMs)
        assertEquals(1L, session.snapshot.ocrCompletedFrames)
        assertEquals(0L, session.snapshot.ocrMissFrames)

        assertTrue(session.frame("a", 210))
        assertNull(session.snapshot.lastCompletedOcrAt)
        assertNull(session.snapshot.lastOcrLatencyMs)
        assertTrue(session.recognized("a", 2, 210, 260, null))
        assertEquals(50L, session.snapshot.maxOcrLatencyMs)
        assertEquals(1L, session.snapshot.ocrMissFrames)
        assertFalse(session.recognized("a", 2, 210, 261, HealthCandidate(15, 20, 0)))
        assertEquals(2L, session.snapshot.ocrCompletedFrames)

        // A five-second-late callback is not fresh OCR evidence or an OCR miss.
        assertTrue(session.frame("a", 310))
        assertFalse(session.recognized("a", 3, 310, 5311, HealthCandidate(11, 20, 0)))
        assertEquals(1L, session.snapshot.ocrLateCallbacks)
        assertEquals(2L, session.snapshot.ocrCompletedFrames)
        assertNull(session.snapshot.lastCompletedFrameAt)
        assertNull(session.snapshot.lastCompletedOcrAt)

        assertTrue(session.frame("a", 5400))
        assertTrue(session.recognized("a", 4, 5400, 5425, HealthCandidate(9, 20, 0)))
        session.visibility("a", false, 5500)
        assertEquals(5425L, session.snapshot.lastCompletedOcrAt)
        session.visibility("a", true, 5600)
        assertNull(session.snapshot.lastCompletedOcrAt)
        assertNull(session.snapshot.lastOcrLatencyMs)
        assertEquals(3L, session.snapshot.ocrCompletedFrames)
        session.stop("USER_STOP")
        assertEquals(3L, session.snapshot.ocrCompletedFrames)
        session.start("b", 6000)
        assertEquals(0L, session.snapshot.ocrCompletedFrames)
        assertEquals(0L, session.snapshot.ocrLateCallbacks)
    }

    @Test fun `completed test retains processing counters but never retained health or game trust`() {
        val session = visibleSession()
        assertTrue(session.frame("a", 110))
        assertTrue(session.recognized("a", 1, 110, 160, HealthCandidate(13, 20, 0)))
        assertTrue(session.frame("a", 210))
        assertTrue(session.recognized("a", 2, 210, 240, null))
        assertTrue(session.frame("a", 310))
        assertFalse(session.recognized("a", 3, 310, 5311, HealthCandidate(11, 20, 0)))
        session.stop("USER_STOP")
        val summary = session.snapshot
        assertEquals(ObservationStatus.STOPPED, summary.status)
        assertEquals(3L, summary.frames)
        assertEquals(2L, summary.ocrCompletedFrames)
        assertEquals(1L, summary.ocrMissFrames)
        assertEquals(1L, summary.ocrLateCallbacks)
        assertEquals(50L, summary.maxOcrLatencyMs)
        assertNull(summary.captureId)
        assertNull(summary.health)
        assertNull(summary.lastHealth)
        assertNull(summary.lastOcrLatencyMs)
        assertFalse(session.recognized("a", 3, 310, 5312, HealthCandidate(11, 20, 0)))
        assertEquals(summary, session.snapshot)
        session.start("b", 6000)
        assertEquals(0L, session.snapshot.frames)
        assertEquals(0L, session.snapshot.ocrCompletedFrames)
        assertEquals(0L, session.snapshot.ocrMissFrames)
        assertEquals(0L, session.snapshot.ocrLateCallbacks)
        assertNull(session.snapshot.maxOcrLatencyMs)
    }

    @Test fun `deadline stops capture even when no new frames arrive`() {
        val session = visibleSession()
        assertTrue(session.tick(300099))
        assertFalse(session.tick(300100))
        assertEquals(ObservationStatus.STOPPED, session.snapshot.status)
        assertEquals("TIME_LIMIT", session.snapshot.reason)
    }

    @Test fun `backwards timestamps are rejected`() {
        val session = visibleSession()
        assertFalse(session.frame("a", 99))
        assertTrue(session.frame("a", 110))
        assertFalse(session.frame("a", 109))
        assertFalse(session.recognized("a", 1, 110, 109, HealthCandidate(4, 20, 0)))
    }

    @Test fun `invalid geometry is rejected and large frames are bounded preserving aspect`() {
        assertNull(CaptureSize.fit(0, 100))
        assertNull(CaptureSize.fit(Int.MAX_VALUE, 100))
        assertEquals(CaptureSize(576, 1280), CaptureSize.fit(1080, 2400))
        assertEquals(CaptureSize(1280, 576), CaptureSize.fit(2400, 1080))
    }

    @Test fun `completed OCR evidence survives a paused stale interval but not resume`() {
        val session = visibleSession()
        assertTrue(session.frame("a", 110))
        assertTrue(session.recognized("a", 1, 110, 111, null))
        session.visibility("a", false, 120)
        assertEquals(110L, session.snapshot.lastCompletedFrameAt)
        assertTrue(session.tick(6000))
        assertEquals(1L, session.snapshot.lastCompletedFrameSequence)
        assertEquals(110L, session.snapshot.lastCompletedFrameAt)
        session.visibility("a", true, 6010)
        assertNull(session.snapshot.lastCompletedFrameSequence)
        assertNull(session.snapshot.lastCompletedFrameAt)
        assertFalse(session.recognized("a", 1, 110, 6011, null))
    }

    @Test fun `resize and Stop erase completed OCR timestamps`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.recognized("a", 1, 110, 111, null)
        session.invalidate("a")
        assertNull(session.snapshot.lastCompletedFrameAt)
        session.frame("a", 120)
        session.recognized("a", 2, 120, 121, null)
        session.stop("USER_STOP")
        assertNull(session.snapshot.lastCompletedFrameAt)
    }

    private fun visibleSession() = ObservationSession().apply {
        start("a", 100)
        visibility("a", true, 101)
    }

    @Test fun `one completed OCR callback including a miss cannot be overwritten`() {
        val session = visibleSession()
        session.frame("a", 110)
        assertNull(session.snapshot.lastCompletedFrameSequence)
        assertTrue(session.recognized("a", 1, 110, 111, null))
        assertEquals(1L, session.snapshot.lastCompletedFrameSequence)
        assertFalse(session.recognized("a", 1, 110, 112, HealthCandidate(4, 20, 0)))
        assertNull(session.snapshot.health)
        session.frame("a", 120)
        assertNull(session.snapshot.lastCompletedFrameSequence)
    }

    @Test fun `rotation invalidates pending recognition from the previous geometry`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.invalidate("a")
        assertFalse(session.recognized("a", 1, 110, 120, HealthCandidate(4, 20, 0)))
        assertTrue(session.frame("a", 130))
        assertTrue(session.recognized("a", 2, 130, 140, HealthCandidate(4, 20, 0)))
    }

    @Test fun `hiding and showing content cannot revive an old OCR result`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.visibility("a", false, 120)
        session.visibility("a", true, 130)
        assertFalse(session.recognized("a", 1, 110, 140, HealthCandidate(4, 20, 0)))
        assertNull(session.snapshot.health)
    }

    @Test fun `a historical candidate is labelled separately from live state and cleared on stop`() {
        val session = visibleSession()
        session.frame("a", 110)
        session.recognized("a", 1, 110, 120, HealthCandidate(4, 20, 0))
        session.visibility("a", false, 130)
        assertNull(session.snapshot.health)
        assertEquals(HealthCandidate(4, 20, 0), session.snapshot.lastHealth?.candidate)
        assertEquals(110L, session.snapshot.lastHealth?.observedAt)
        assertEquals(110L, session.snapshot.lastRecognizedFrameAt)
        session.stop("USER_STOP")
        assertNull(session.snapshot.lastHealth)
        assertNull(session.snapshot.lastRecognizedFrameAt)
    }
}
