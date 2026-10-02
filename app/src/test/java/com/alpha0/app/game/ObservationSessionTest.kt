package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class ObservationSessionTest {
    @Test fun `frames require an active visible session`() {
        val session = ObservationSession()
        assertFalse(session.frame("a", 10))
        session.start("a", 100)
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

    private fun visibleSession() = ObservationSession().apply {
        start("a", 100)
        visibility("a", true, 101)
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
        session.stop("USER_STOP")
        assertNull(session.snapshot.lastHealth)
    }
}
