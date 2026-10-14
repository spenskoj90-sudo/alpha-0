package com.alpha0.app.game

enum class ObservationStatus { STOPPED, WAITING, OBSERVING, PAUSED, FAILED }
data class HealthCandidate(val current: Int, val maximum: Int, val shield: Int)
data class HealthObservation(val candidate: HealthCandidate, val observedAt: Long)
data class ObservationSnapshot(
    val status: ObservationStatus = ObservationStatus.STOPPED,
    val reason: String = "USER_STOP",
    /** Process-local capture generation, never an authority or external identity. */
    val captureId: String? = null,
    val frames: Long = 0,
    val lastFrameAt: Long? = null,
    val health: HealthCandidate? = null,
    val lastHealth: HealthObservation? = null,
    /** Last completed non-null OCR frame; cleared by a newer frame, miss, or geometry change. */
    val lastRecognizedFrameAt: Long? = null,
    /** Only a completed OCR callback (including a confirmed miss) can be sampled. */
    val lastCompletedFrameSequence: Long? = null,
)
data class CaptureSize(val width: Int, val height: Int) {
    companion object {
        fun fit(width: Int, height: Int): CaptureSize? {
            if (width !in 1..16384 || height !in 1..16384) return null
            val scale = minOf(1.0, 1280.0 / maxOf(width, height))
            return CaptureSize(maxOf(1, (width * scale).toInt()), maxOf(1, (height * scale).toInt()))
        }
    }
}

/** Local observation only. No authorization, entitlement, or game-action interface. */
class ObservationSession {
    @Volatile var snapshot = ObservationSnapshot(); private set
    private var sessionId: String? = null
    private var startedAt = 0L
    @Synchronized fun invalidate(id: String) {
        if (id == sessionId) snapshot = snapshot.copy(health = null, lastFrameAt = null, lastRecognizedFrameAt = null, lastCompletedFrameSequence = null)
    }

    @Synchronized fun start(id: String, now: Long) {
        require(id.isNotBlank() && id.length <= 64 && now >= 0)
        sessionId = id
        startedAt = now
        snapshot = ObservationSnapshot(status = ObservationStatus.WAITING, reason = "WAITING_FOR_SOURCE", captureId = id)
    }

    @Synchronized fun visibility(id: String, visible: Boolean, now: Long) {
        if (id != sessionId || !tick(now)) return
        snapshot = snapshot.copy(
            status = if (visible) ObservationStatus.OBSERVING else ObservationStatus.PAUSED,
            reason = if (visible) "SOURCE_VISIBLE" else "SOURCE_HIDDEN",
            health = null,
            lastFrameAt = if (visible) snapshot.lastFrameAt else null,
            lastRecognizedFrameAt = if (visible) null else snapshot.lastRecognizedFrameAt,
            lastCompletedFrameSequence = if (visible) null else snapshot.lastCompletedFrameSequence,
        )
    }

    @Synchronized fun frame(id: String, now: Long): Boolean {
        if (id != sessionId || now < startedAt || !tick(now) || snapshot.status != ObservationStatus.OBSERVING) return false
        if (now < (snapshot.lastFrameAt ?: startedAt)) return false
        snapshot = snapshot.copy(frames = snapshot.frames + 1, lastFrameAt = now, health = null, lastRecognizedFrameAt = null, lastCompletedFrameSequence = null)
        return true
    }

    @Synchronized fun recognized(
        id: String, sequence: Long, frameAt: Long, now: Long, health: HealthCandidate?,
    ): Boolean {
        if (id != sessionId || !tick(now) || snapshot.status != ObservationStatus.OBSERVING) return false
        if (sequence != snapshot.frames || sequence == snapshot.lastCompletedFrameSequence || frameAt != snapshot.lastFrameAt || now < frameAt || now - frameAt > 5000) return false
        snapshot = snapshot.copy(health = health, lastHealth = health?.let { HealthObservation(it, frameAt) } ?: snapshot.lastHealth,
            lastRecognizedFrameAt = if (health == null) null else frameAt, lastCompletedFrameSequence = sequence)
        return true
    }

    @Synchronized fun tick(now: Long): Boolean {
        if (sessionId == null) return false
        if (now < startedAt || now - startedAt >= 300000) {
            stop(if (now < startedAt) "CLOCK_INVALID" else "TIME_LIMIT")
            return false
        }
        if (snapshot.lastFrameAt?.let { now - it > 5000 } == true) snapshot = snapshot.copy(health = null)
        return true
    }

    @Synchronized fun stop(reason: String) {
        sessionId = null
        snapshot = snapshot.copy(status = ObservationStatus.STOPPED, reason = reason, captureId = null, health = null,
            lastHealth = null, lastRecognizedFrameAt = null, lastCompletedFrameSequence = null)
    }
}
