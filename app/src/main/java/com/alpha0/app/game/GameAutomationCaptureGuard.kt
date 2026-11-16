package com.alpha0.app.game

/** Fail-closed action-side fence for service-originated MediaProjection events.
 * The service supplies the current session generation. A UI-provided ID never
 * establishes source trust or authorizes game input.
 */
internal object GameAutomationCaptureGuard {
    private fun mayHaveActiveEvidence(snapshot: ObservationSnapshot, captureId: String): Boolean =
        captureId.isNotBlank() && snapshot.captureId == captureId &&
            snapshot.frames > 0L && snapshot.status in setOf(
                ObservationStatus.OBSERVING, ObservationStatus.PAUSED,
            )

    fun onVisibilityChanged(
        snapshot: ObservationSnapshot,
        captureId: String,
        isVisible: Boolean,
        latch: GameAutomationStopLatch,
    ) {
        if (!isVisible && mayHaveActiveEvidence(snapshot, captureId))
            latch.stop(captureId)
    }

    fun onGeometryChanged(
        snapshot: ObservationSnapshot,
        captureId: String,
        latch: GameAutomationStopLatch,
    ) {
        if (mayHaveActiveEvidence(snapshot, captureId))
            latch.stop(captureId)
    }
}
