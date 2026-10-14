package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class CalibrationCampaignTest {
    private fun frame(sequence: Long, capture: String = "capture") = CalibrationFrameId(capture, sequence)

    @Test fun `missing and stale samples remain in the denominator`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("-1", "20", null, 100, frame(1)))
        val missing = campaign.record("4", "20", null, 100, frame(1))!!
        assertNull(missing.observed)
        val stale = campaign.record("4", "20", HealthObservation(HealthCandidate(3, 20, 0), 100), 10000, frame(2))!!
        assertEquals(9900L, stale.ageMs)
        assertEquals(2, campaign.count)
    }

    @Test fun `campaign bounds inputs and records at most 32 opt in samples`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("99999999999", "20", null, 1, frame(1)))
        assertNull(campaign.record("21", "20", null, 1, frame(1)))
        assertNull(campaign.record("4", "0", null, 1, frame(1)))
        repeat(32) { assertNotNull(campaign.record("4", "20", null, 1, frame(it + 1L))) }
        assertNull(campaign.record("4", "20", null, 1, frame(33)))
        assertEquals(32, campaign.count)
    }

    @Test fun `future timestamps cannot produce a measurement`() {
        assertNull(CalibrationCampaign().record("4", "20", HealthObservation(HealthCandidate(4, 20, 0), 200), 100, frame(1)))
    }

    @Test fun `failed writes do not increment saved count or consume the frame`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(1)) { false })
        assertNull(campaign.record("4", "20", null, 100, frame(1)) { throw IllegalStateException("storage unavailable") })
        assertEquals(0, campaign.count)
        assertEquals(1, campaign.record("4", "20", null, 100, frame(1)) { true }!!.sequence)
        assertEquals(1, campaign.count)
    }

    @Test fun `repeated saves of same recognized or missing frame cannot inflate sample count`() {
        val campaign = CalibrationCampaign()
        val observed = HealthObservation(HealthCandidate(4, 20, 0), 100)
        assertNotNull(campaign.record("4", "20", observed, 110, frame(1)))
        assertNull(campaign.record("4", "20", observed, 120, frame(1)))
        assertNotNull(campaign.record("5", "20", null, 130, frame(2)))
        assertNull(campaign.record("5", "20", null, 131, frame(2)))
        assertEquals(2, campaign.count)
    }

    @Test fun `one campaign rejects cross-session samples and invalid frame provenance`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("4", "20", null, 100, frame(0)))
        assertNull(campaign.record("4", "20", null, 100, frame(1, "")))
        assertNotNull(campaign.record("4", "20", null, 100, frame(1)))
        assertNull(campaign.record("4", "20", null, 101, frame(1, "other")))
        assertEquals(1, campaign.count)
    }
}
