package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class CalibrationCampaignTest {
    @Test fun `missing and stale samples remain in the denominator`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("-1", "20", null, 100))
        val missing = campaign.record("4", "20", null, 100)!!
        assertNull(missing.observed)
        val stale = campaign.record("4", "20", HealthObservation(HealthCandidate(3, 20, 0), 100), 10000)!!
        assertEquals(9900L, stale.ageMs)
        assertEquals(2, campaign.count)
    }
    @Test fun `campaign bounds inputs and records at most 32 opt in samples`() {
        val campaign = CalibrationCampaign()
        assertNull(campaign.record("99999999999", "20", null, 1))
        assertNull(campaign.record("21", "20", null, 1))
        assertNull(campaign.record("4", "0", null, 1))
        repeat(32) { assertNotNull(campaign.record("4", "20", null, 1)) }
        assertNull(campaign.record("4", "20", null, 1))
        assertEquals(32, campaign.count)
    }
    @Test fun `future timestamps cannot produce a measurement`() {
        assertNull(CalibrationCampaign().record("4", "20", HealthObservation(HealthCandidate(4, 20, 0), 200), 100))
    }
}
