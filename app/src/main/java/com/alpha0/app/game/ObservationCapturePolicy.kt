package com.alpha0.app.game

/** Explicit consent-only screen capture availability; this check never grants
 * trusted game source identity, knowledge or game:write authority. */
internal object ObservationCapturePolicy {
    fun supports(debuggable: Boolean, channel: String, apiLevel: Int): Boolean =
        apiLevel >= 34 && when (channel) {
            "development", "diagnostic" -> debuggable
            "signed_feed" -> !debuggable
            else -> false
        }
}
