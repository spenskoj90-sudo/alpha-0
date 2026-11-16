package com.alpha0.app.game

/** Explicit consent-only screen capture availability; this check never grants
 * trusted game source identity, knowledge or game:write authority. */
internal object ObservationCapturePolicy {
    /** Recheck what the user actually acknowledged before showing Android's
     * system capture chooser. This checks installed APK metadata only; it does
     * not attest the screen/window selected in MediaProjection. */
    fun canRequestConsent(
        supported: Boolean, acknowledged: Boolean,
        displayed: StockGameInstall?, installedNow: StockGameInstall?,
    ): Boolean = supported && acknowledged && displayed != null && displayed == installedNow

    fun supports(debuggable: Boolean, channel: String, apiLevel: Int): Boolean =
        apiLevel >= 34 && when (channel) {
            "development", "diagnostic" -> debuggable
            "signed_feed" -> !debuggable
            else -> false
        }
}
