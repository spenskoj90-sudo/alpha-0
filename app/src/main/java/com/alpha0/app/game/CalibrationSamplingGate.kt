package com.alpha0.app.game

/** A comparison is tied to one completed capture generation and frame, not to
 * a button press. Missing OCR is a legitimate negative sample once a frame exists.
 * This is metadata fencing, not screen-source or game attestation.
 */
internal object CalibrationSamplingGate {
    fun frameId(snapshot: ObservationSnapshot): CalibrationFrameId? {
        if (snapshot.status !in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED)) return null
        val captureId = snapshot.captureId?.takeIf { it.isNotBlank() } ?: return null
        if (snapshot.frames < 1) return null
        return CalibrationFrameId(captureId, snapshot.frames)
    }

    fun canSample(snapshot: ObservationSnapshot, captured: StockGameInstall?, installed: StockGameInstall?): Boolean =
        frameId(snapshot) != null && captured != null && captured == installed

    fun current(snapshot: ObservationSnapshot): HealthObservation? {
        val last = snapshot.lastHealth ?: return null
        if (snapshot.lastRecognizedFrameAt != last.observedAt) return null
        return when (snapshot.status) {
            ObservationStatus.OBSERVING -> last.takeIf {
                snapshot.health == last.candidate && snapshot.lastFrameAt == last.observedAt
            }
            ObservationStatus.PAUSED -> last // historical: the sample age determines staleness
            else -> null
        }
    }
}
