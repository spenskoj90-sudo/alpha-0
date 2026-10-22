package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

/** Models Compose panel destruction/recreation while the foreground service stays alive. */
class CalibrationCampaignRegistryTest {
    private val install = StockGameInstall("3.3.0", 300L, "a".repeat(64))
    private val changedSigner = StockGameInstall("3.3.0", 300L, "b".repeat(64))

    @Test fun `panel recreation preserves capture campaign and diagnostic sample sequence`() {
        val registry = CalibrationCampaignRegistry()
        val first = registry.forCapture("capture-one", install)
        assertNotNull(first.campaign.record("4", "20", null, 100, CalibrationFrameId("capture-one", 1), 100))
        val remounted = registry.forCapture("capture-one", install)
        assertSame(first, remounted)
        assertEquals(first.campaignId, remounted.campaignId)
        assertEquals(1, remounted.campaign.count)
        // A remounted panel must not log the same capture frame again.
        assertNull(remounted.campaign.record("4", "20", null, 110, CalibrationFrameId("capture-one", 1), 100))
        val next = remounted.campaign.record("4", "20", null, 120, CalibrationFrameId("capture-one", 2), 115)
        assertNotNull(next)
        assertEquals(2, next!!.sequence)
    }

    @Test fun `recreation cannot reset the 32 sample ceiling`() {
        val registry = CalibrationCampaignRegistry()
        val first = registry.forCapture("capture-one", install)
        repeat(32) { index ->
            assertNotNull(first.campaign.record("4", "20", null, 100, CalibrationFrameId("capture-one", index + 1L), 100))
        }
        val remounted = registry.forCapture("capture-one", install)
        assertSame(first.campaign, remounted.campaign)
        assertEquals(32, remounted.campaign.count)
        assertNull(remounted.campaign.record("4", "20", null, 100, CalibrationFrameId("capture-one", 33), 100))
    }

    @Test fun `new capture changed signer and stop each reset local campaign identity`() {
        val registry = CalibrationCampaignRegistry()
        val first = registry.forCapture("capture-one", install)
        assertNotSame(first, registry.forCapture("capture-two", install))
        val second = registry.forCapture("capture-two", install)
        val replaced = registry.forCapture("capture-two", changedSigner)
        assertNotSame(second, replaced)
        assertNotEquals(second.campaignId, replaced.campaignId)
        assertEquals(0, replaced.campaign.count)
        registry.clear() // Stop / revocation / account boundary
        val afterStop = registry.forCapture("capture-two", changedSigner)
        assertNotSame(replaced, afterStop)
        assertNotEquals(replaced.campaignId, afterStop.campaignId)
        assertEquals(0, afterStop.campaign.count)
    }
}
