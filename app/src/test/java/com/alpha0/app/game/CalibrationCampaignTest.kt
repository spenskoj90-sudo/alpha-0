package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class CalibrationCampaignTest {
    private fun frame(sequence: Long, capture: String = "capture") = CalibrationFrameId(capture, sequence)

    @Test fun `missing and stale samples remain in the denominator`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("-1", "20", null, 100, frame(1), 100))
        val missing = campaign.record("4", "20", null, 100, frame(1), 100)!!
        assertNull(missing.observed)
        assertEquals(0L, missing.ageMs)
        val agedMiss = campaign.record("4", "20", null, 10000, frame(2), 100)!!
        assertNull(agedMiss.observed)
        assertEquals(9900L, agedMiss.ageMs)
        val stale = campaign.record("4", "20", HealthObservation(HealthCandidate(3, 20, 0), 100), 10000, frame(3), 100)!!
        assertEquals(9900L, stale.ageMs)
        assertEquals(3, campaign.count)
    }

    @Test fun `campaign bounds inputs and records at most 32 opt in samples`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("99999999999", "20", null, 1, frame(1), 1))
        assertNull(campaign.record("21", "20", null, 1, frame(1), 1))
        assertNull(campaign.record("4", "0", null, 1, frame(1), 1))
        repeat(32) { assertNotNull(campaign.record("4", "20", null, 1, frame(it + 1L), 1)) }
        assertNull(campaign.record("4", "20", null, 1, frame(33), 1))
        assertEquals(32, campaign.count)
    }

    @Test fun `OCR misses need actual frame time and reject future or expired evidence`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(1), null))
        assertNull(campaign.record("4", "20", null, 100, frame(1), 101))
        assertNull(campaign.record("4", "20", null, 300101, frame(1), 100))
        assertEquals(0, campaign.count)
    }

    @Test fun `recognized candidate must match completed frame timestamp`() {
        val observed = HealthObservation(HealthCandidate(4, 20, 0), 100)
        assertNull(CalibrationCampaign().record("4", "20", observed, 120, frame(1), 110))
    }

    @Test fun `future timestamps cannot produce a measurement`() {
        assertNull(CalibrationCampaign().record("4", "20", HealthObservation(HealthCandidate(4, 20, 0), 200), 100, frame(1), 200))
    }

    @Test fun `failed writes do not increment saved count or consume the frame`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(1), 100) { false })
        assertNull(campaign.record("4", "20", null, 100, frame(1), 100) { throw IllegalStateException("storage unavailable") })
        assertEquals(0, campaign.count)
        assertEquals(1, campaign.record("4", "20", null, 100, frame(1), 100) { true }!!.sequence)
        assertEquals(1, campaign.count)
    }

    @Test fun `repeated saves of same recognized or missing frame cannot inflate sample count`() {
        val campaign = CalibrationCampaign()
        val observed = HealthObservation(HealthCandidate(4, 20, 0), 100)
        assertNotNull(campaign.record("4", "20", observed, 110, frame(1), 100))
        assertNull(campaign.record("4", "20", observed, 120, frame(1), 100))
        assertNotNull(campaign.record("5", "20", null, 130, frame(2), 130))
        assertNull(campaign.record("5", "20", null, 131, frame(2), 131))
        assertEquals(2, campaign.count)
    }

    @Test fun `saved numeric sample exposes only frame identity and monotonic capture metadata`() {
        val campaign = CalibrationCampaign()
        val sample = campaign.record("4", "20", HealthObservation(HealthCandidate(3, 20, 0), 100),
            170, frame(5), 100)!!
        assertEquals("capture", sample.captureId)
        assertEquals(5L, sample.frameSequence)
        assertEquals(100L, sample.capturedAtMs)
        assertEquals(170L, sample.savedAtMs)
        assertEquals(sample.savedAtMs - sample.capturedAtMs, sample.ageMs)
        assertEquals(1, sample.sequence)
        // Old frames may not be inserted after a newer accepted frame.
        assertNull(campaign.record("4", "20", null, 180, frame(4), 180))
        assertEquals(1, campaign.count)
        assertEquals(2, campaign.record("4", "20", null, 200, frame(6), 200)!!.sequence)
    }

    @Test fun `a failed diagnostic write does not advance the frame sequence fence`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(5), 100) { false })
        val stored = campaign.record("4", "20", null, 110, frame(5), 100) { true }!!
        assertEquals(5L, stored.frameSequence)
        assertEquals(2, campaign.record("4", "20", null, 120, frame(6), 120)!!.sequence)
    }

    @Test fun `one campaign rejects cross-session samples and invalid frame provenance`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(0), 100))
        assertNull(campaign.record("4", "20", null, 100, frame(1, ""), 100))
        assertNotNull(campaign.record("4", "20", null, 100, frame(1), 100))
        assertNull(campaign.record("4", "20", null, 101, frame(1, "other"), 101))
        assertEquals(1, campaign.count)
    }

    @Test fun `capture and save times cannot regress within a campaign`() {
        val campaign = CalibrationCampaign()
        assertNotNull(campaign.record("4", "20", null, 120, frame(5), 100))
        var persisted = 0
        // A newer frame ID does not permit an older acquisition timestamp.
        assertNull(campaign.record("4", "20", null, 130, frame(6), 99) {
            persisted++; true
        })
        // Nor may the Save clock move backwards, even if the frame is newer.
        assertNull(campaign.record("4", "20", null, 119, frame(6), 110) {
            persisted++; true
        })
        assertEquals(0, persisted)
        assertEquals(1, campaign.count)
        assertNotNull(campaign.record("4", "20", null, 130, frame(6), 110))
        assertEquals(2, campaign.count)
    }

    @Test fun `failed writes do not move either chronology fence`() {
        val campaign = CalibrationCampaign()
        assertNotNull(campaign.record("4", "20", null, 120, frame(1), 100))
        assertNull(campaign.record("4", "20", null, 200, frame(2), 190) { false })
        // The failed frame's timestamp must not poison an otherwise valid retry.
        val retry = campaign.record("4", "20", null, 130, frame(2), 110)
        assertNotNull(retry)
        assertEquals(110L, retry!!.capturedAtMs)
        assertEquals(130L, retry.savedAtMs)
        assertEquals(2, campaign.count)
    }
}
