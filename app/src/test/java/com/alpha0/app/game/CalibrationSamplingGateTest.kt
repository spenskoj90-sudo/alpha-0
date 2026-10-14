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
        assertTrue(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, repack))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, game, null))
        assertFalse(CalibrationSamplingGate.canSample(session.snapshot, null, game))
        session.visibility("observing", false, 102)
        assertTrue(CalibrationSamplingGate.canSample(session.snapshot, game, game))
        session.stop("USER_STOP")
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

