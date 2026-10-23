package com.alpha0.app.game

/** A comparison is tied to one completed capture generation and frame, not to
 * a button press. Missing OCR is a legitimate negative sample once a frame exists.
 * This is metadata fencing, not screen-source or game attestation.
 */
/** Timing of the last *completed* frame, not an estimate of action-to-response time.
 * Age since OCR also includes app switching, form entry and other human time.
 */
internal data class CalibrationTimingBreakdown(
    val frameAgeMs: Long,
    val processingMs: Long,
    val afterOcrMs: Long,
)

internal object CalibrationSamplingGate {
    fun frameId(snapshot: ObservationSnapshot): CalibrationFrameId? {
        if (snapshot.status !in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED)) return null
        val captureId = snapshot.captureId?.takeIf { it.isNotBlank() } ?: return null
        if (snapshot.frames < 1 || snapshot.lastCompletedFrameSequence != snapshot.frames ||
            snapshot.lastCompletedFrameAt == null || snapshot.lastCompletedFrameAt < 0) return null
        return CalibrationFrameId(captureId, snapshot.frames)
    }

    fun canSample(snapshot: ObservationSnapshot, captured: StockGameInstall?, installed: StockGameInstall?): Boolean =
        frameId(snapshot) != null && captured != null && captured == installed

    /** Never display a duration if the callback belongs to another/invalid frame. */
    fun timing(snapshot: ObservationSnapshot, now: Long): CalibrationTimingBreakdown? {
        if (frameId(snapshot) == null || now < 0) return null
        val frameAt = snapshot.lastCompletedFrameAt ?: return null
        val completedAt = snapshot.lastCompletedOcrAt ?: return null
        val processingMs = snapshot.lastOcrLatencyMs ?: return null
        if (completedAt < frameAt || completedAt > now ||
            processingMs != completedAt - frameAt || processingMs !in 0L..5000L ||
            now - frameAt !in 0L..300000L) return null
        return CalibrationTimingBreakdown(now - frameAt, processingMs, now - completedAt)
    }

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
