package com.alpha0.app.game

import java.util.UUID

/** Process-local numeric comparison state for one capture and installed game identity.
 * Recreating the Compose panel (for example on device rotation) must not start a new
 * campaign or reset its 32-sample limit. No samples or capture IDs are persisted here.
 */
internal class CalibrationCampaignRegistry {
    internal data class Run(
        val captureId: String?,
        val install: StockGameInstall?,
        val campaignId: String,
        val campaign: CalibrationCampaign,
    )

    private var active: Run? = null

    @Synchronized
    fun forCapture(captureId: String?, install: StockGameInstall?): Run {
        val previous = active
        if (previous != null && previous.captureId == captureId && previous.install == install)
            return previous
        return Run(captureId, install, UUID.randomUUID().toString(), CalibrationCampaign())
            .also { active = it }
    }

    /** Stop/revocation/account transition must drop retained diagnostic state. */
    @Synchronized
    fun clear() {
        active = null
    }
}
