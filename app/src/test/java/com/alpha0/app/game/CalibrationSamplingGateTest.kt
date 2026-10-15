package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

/** Never inflate calibration agreement from a stopped/hidden or superseded OCR candidate. */
class CalibrationSamplingGateTest {
    private val game = StockGameInstall("3.3.0", 300L, "a".repeat(64))
    private val repack = StockGameInstall("3.3.0", 300L, "b".repeat(64))

    @Test fun `save requires live capture and exact install including signer`() {
        val session = ObservationSession()
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        session.start("observing", 100)
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        session.visibility("observing", true, 101)
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game)) // no captured frame yet
        assertTrue(session.frame("observing", 101))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game)) // OCR still pending
        assertTrue(session.recognized("observing", 1, 101, 102, null))
        assertTrue(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, repack))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, null))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, null, game))
        session.visibility("observing", false, 102)
        assertTrue(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        session.stop("USER_STOP")
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
    }

    @Test fun `frame identity survives pause but changes on each completed frame and capture`() {
        val session = ObservationSession()
        session.start("first", 100)
        session.visibility("first", true, 101)
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
        session.frame("first", 110)
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
        session.recognized("first", 1, 110, 111, null)
        val first = CalibrationSamplingGate.frameId(session.snapshot)
        assertEquals(CalibrationFrameId("first", 1L), first)
        session.visibility("first", false, 120)
        assertEquals(first, CalibrationSamplingGate.frameId(session.snapshot))
        session.visibility("first", true, 130)
        session.frame("first", 140)
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
        session.recognized("first", 2, 140, 141, null)
        assertEquals(CalibrationFrameId("first", 2L), CalibrationSamplingGate.frameId(session.snapshot))
        session.start("second", 200)
        session.visibility("second", true, 201)
        session.frame("second", 210)
        session.recognized("second", 1, 210, 211, null)
        assertEquals(CalibrationFrameId("second", 1L), CalibrationSamplingGate.frameId(session.snapshot))
    }

    @Test fun `paused OCR miss retains its exact source timestamp while stale`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        session.frame("capture", 110)
        session.recognized("capture", 1, 110, 111, null)
        session.visibility("capture", false, 120)
        session.tick(10000)
        assertEquals(CalibrationFrameId("capture", 1), CalibrationSamplingGate.frameId(session.snapshot))
        assertEquals(110L, session.snapshot.lastCompletedFrameAt)
        val sample = CalibrationCampaign().record("4", "20", CalibrationSamplingGate.current(session.snapshot), 10000,
            CalibrationSamplingGate.frameId(session.snapshot)!!, session.snapshot.lastCompletedFrameAt)!!
        assertNull(sample.observed)
        assertEquals(9890L, sample.ageMs)
    }

    @Test fun `pending OCR cannot be counted as a negative sample after pause`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        session.frame("capture", 110)
        session.visibility("capture", false, 111)
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
        assertFalse(session.recognized("capture", 1, 110, 112, null))
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
    }

    @Test fun `expired completed frame cannot be relabelled a fresh OCR miss`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        session.frame("capture", 110)
        session.recognized("capture", 1, 110, 120, HealthCandidate(4, 20, 0))
        assertNotNull(CalibrationSamplingGate.frameId(session.snapshot))
        session.tick(5111)
        assertNull(CalibrationSamplingGate.frameId(session.snapshot))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, game))
    }

    @Test fun `historical health never becomes an active sample for later frame`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        assertTrue(session.frame("capture", 110))
        assertTrue(session.recognized("capture", 1, 110, 111, HealthCandidate(4, 20, 0)))
        assertEquals(HealthCandidate(4, 20, 0), CalibrationSamplingGate.current(session.snapshot)?.candidate)
        assertTrue(session.frame("capture", 120))
        assertNull(CalibrationSamplingGate.current(session.snapshot))
        // A second frame can fail OCR while the session remains visible.
        assertTrue(session.recognized("capture", 2, 120, 121, null))
        assertNull(CalibrationSamplingGate.current(session.snapshot))
        assertTrue(session.frame("capture", 130))
        assertTrue(session.recognized("capture", 3, 130, 131, HealthCandidate(5, 20, 0)))
        assertEquals(HealthCandidate(5, 20, 0), CalibrationSamplingGate.current(session.snapshot)?.candidate)
    }

    @Test fun `hidden and expired observations do not count as fresh`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        session.frame("capture", 110)
        session.recognized("capture", 1, 110, 120, HealthCandidate(6, 20, 0))
        session.visibility("capture", false, 121)
        assertNotNull(session.snapshot.lastHealth)
        // A phone can switch from the selected game to the SENTINEL input form.
        // The completed result remains explicitly historical (its age is retained).
        assertEquals(110L, CalibrationSamplingGate.current(session.snapshot)?.observedAt)
        session.tick(5200)
        assertEquals(110L, CalibrationSamplingGate.current(session.snapshot)?.observedAt)
        session.visibility("capture", true, 5201)
        assertNull(CalibrationSamplingGate.current(session.snapshot))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, repack))
    }

    @Test fun `paused capture cannot reuse old OCR after an unrecognized newer frame`() {
        val session = ObservationSession()
        session.start("capture", 100)
        session.visibility("capture", true, 101)
        session.frame("capture", 110)
        session.recognized("capture", 1, 110, 111, HealthCandidate(4, 20, 0))
        session.frame("capture", 120)
        session.visibility("capture", false, 121)
        assertNotNull(session.snapshot.lastHealth)
        assertNull(CalibrationSamplingGate.current(session.snapshot))
        session.visibility("capture", true, 122)
        session.frame("capture", 130)
        session.recognized("capture", 3, 130, 131, null)
        session.visibility("capture", false, 132)
        assertNull(CalibrationSamplingGate.current(session.snapshot))
    }
}

