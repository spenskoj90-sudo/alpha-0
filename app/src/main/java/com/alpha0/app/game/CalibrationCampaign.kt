package com.alpha0.app.game

/** A single screen frame may contribute at most one successful numeric comparison. */
data class CalibrationFrameId(val captureId: String, val sequence: Long)

/** Opt-in numeric comparisons only. No pixels, raw OCR or action authority. */
data class CalibrationSample(
    val sequence: Int,
    val ageMs: Long,
    val observed: HealthCandidate?,
    val current: Int,
    val maximum: Int,
    /** Per-session, non-identifying capture frame provenance for diagnostic review only. */
    val captureId: String,
    val frameSequence: Long,
    val capturedAtMs: Long,
    val savedAtMs: Long,
)
class CalibrationCampaign {
    var count = 0; private set
    private val savedFrames = mutableSetOf<CalibrationFrameId>()
    private var boundCaptureId: String? = null
    private var lastSavedFrameSequence = 0L
    private var lastSavedCapturedAt = -1L
    private var lastSavedAt = -1L

    fun record(
        currentText: String, maximumText: String, observation: HealthObservation?,
        now: Long, frameId: CalibrationFrameId, frameAt: Long?,
        persist: (CalibrationSample) -> Boolean = { true },
    ): CalibrationSample? {
        if (count >= 32 || currentText.length > 6 || maximumText.length > 6 || now < 0) return null
        if (frameId.captureId.isBlank() || frameId.captureId.length > 64 ||
            frameId.sequence <= lastSavedFrameSequence || frameId in savedFrames ||
            (boundCaptureId != null && boundCaptureId != frameId.captureId)) return null
        if (!currentText.matches(Regex("[0-9]{1,6}")) || !maximumText.matches(Regex("[0-9]{1,6}"))) return null
        val current = currentText.toIntOrNull() ?: return null
        val maximum = maximumText.toIntOrNull() ?: return null
        if (maximum !in 1..999999 || current !in 0..maximum) return null
        // Even an OCR miss has a capture timestamp. Never report an old frame as age 0.
        val capturedAt = frameAt ?: return null
        // The offline importer requires both capture and Save clocks to be
        // nondecreasing. Reject impossible chronology before it reaches diagnostics.
        if (capturedAt < 0 || capturedAt > now ||
            capturedAt < lastSavedCapturedAt || now < lastSavedAt ||
            (observation != null && observation.observedAt != capturedAt)) return null
        val age = now - capturedAt
        if (age !in 0L..300000L) return null
        val sample = CalibrationSample(
            count + 1, age, observation?.candidate, current, maximum,
            frameId.captureId, frameId.sequence, capturedAt, now,
        )
        if (!runCatching { persist(sample) }.getOrDefault(false)) return null
        boundCaptureId = frameId.captureId
        lastSavedFrameSequence = frameId.sequence
        lastSavedCapturedAt = capturedAt
        lastSavedAt = now
        savedFrames.add(frameId)
        count++
        return sample
    }
}
