package com.alpha0.app.game

/** A comparison is tied to one completed capture generation and frame, not to
 * a button press. Missing OCR is a legitimate negative sample once a frame exists.
 * This is metadata fencing, not screen-source or game attestation.
 */
/** Timing of the last *completed* frame, not an estimate of action-to-response time.
 * Age since OCR also includes app switching, form entry and other human time.
 */
internal enum class CalibrationSaveBlockReason(val stringKey: String) {
    CAPTURE_INACTIVE("game_calibration_block_inactive"),
    GAME_CHANGED("game_calibration_block_game_changed"),
    FRAME_UNAVAILABLE("game_calibration_block_frame_unavailable"),
    CLOCK_INVALID("game_calibration_block_clock_invalid"),
    FRAME_EXPIRED("game_calibration_block_frame_expired"),
}

internal data class CalibrationTimingBreakdown(
    val frameAgeMs: Long,
    val processingMs: Long,
    val afterOcrMs: Long,
)

internal object CalibrationSamplingGate {
    fun frameId(snapshot: ObservationSnapshot): CalibrationFrameId? {
        if (snapshot.status !in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED)) return null
        val captureId = snapshot.captureId?.takeIf { it.isNotBlank() } ?: return null
        if (snapshot.frames < 1 || snapshot.lastCompletedFrameSequence != snapshot.frames) return null
        val frameAt = snapshot.lastCompletedFrameAt ?: return null
        val completedAt = snapshot.lastCompletedOcrAt ?: return null
        val latencyMs = snapshot.lastOcrLatencyMs ?: return null
        // A sequence number alone cannot prove a completed current-frame OCR callback.
        // Even an OCR miss requires coherent, bounded capture/completion timestamps.
        // Pausing deliberately clears the live-frame timestamp so a historical
        // comparison cannot be mistaken for live health. Keep the completed OCR
        // timestamp usable for that retrospective comparison only.
        if (frameAt < 0 ||
            (snapshot.status == ObservationStatus.OBSERVING && frameAt != snapshot.lastFrameAt) ||
            completedAt < frameAt || latencyMs !in 0L..5000L ||
            completedAt - frameAt != latencyMs) return null
        return CalibrationFrameId(captureId, snapshot.frames)
    }

    fun canSample(snapshot: ObservationSnapshot, captured: StockGameInstall?, installed: StockGameInstall?): Boolean =
        frameId(snapshot) != null && captured != null && captured == installed

    /** Save authority and the visible blocker use one fail-closed gate. */
    fun saveBlockReason(
        snapshot: ObservationSnapshot, captured: StockGameInstall?,
        installed: StockGameInstall?, now: Long,
    ): CalibrationSaveBlockReason? {
        if (snapshot.status !in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED))
            return CalibrationSaveBlockReason.CAPTURE_INACTIVE
        if (captured == null || captured != installed)
            return CalibrationSaveBlockReason.GAME_CHANGED
        if (frameId(snapshot) == null)
            return CalibrationSaveBlockReason.FRAME_UNAVAILABLE
        val frameAt = snapshot.lastCompletedFrameAt ?: return CalibrationSaveBlockReason.FRAME_UNAVAILABLE
        val completedAt = snapshot.lastCompletedOcrAt ?: return CalibrationSaveBlockReason.FRAME_UNAVAILABLE
        if (now < 0 || frameAt > now || completedAt > now)
            return CalibrationSaveBlockReason.CLOCK_INVALID
        if (now - frameAt > 300000L)
            return CalibrationSaveBlockReason.FRAME_EXPIRED
        return if (timing(snapshot, now) == null) CalibrationSaveBlockReason.FRAME_UNAVAILABLE else null
    }

    /** A Save must recheck the live elapsed clock, not only a rendered frame ID. */
    fun canSave(
        snapshot: ObservationSnapshot, captured: StockGameInstall?,
        installed: StockGameInstall?, now: Long,
    ): Boolean = saveBlockReason(snapshot, captured, installed, now) == null

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
        if (frameId(snapshot) == null) return null
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
