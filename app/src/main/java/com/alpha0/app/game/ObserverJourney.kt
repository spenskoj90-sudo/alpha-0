package com.alpha0.app.game

/** Read-only next step for the diagnostic journey; never grants source or game-action authority. */
internal enum class ObserverNextStep(val stringKey: String) {
    INSTALL_GAME("game_journey_install"),
    DIAGNOSTIC_BUILD("game_journey_build"),
    WAIT_FOR_PERMISSION("game_journey_permission"),
    WAIT_FOR_SOURCE("game_journey_wait_source"),
    SOURCE_HIDDEN("game_journey_hidden"),
    WAIT_FOR_RECOGNITION("game_journey_wait_ocr"),
    SAVE_COMPARISON("game_journey_sample"),
    REVIEW_CALIBRATION("game_journey_review"),
    CONSENT("game_journey_consent"),
    CHOOSE_SOURCE("game_journey_choose"),
}

internal fun observerNextStep(
    installed: Boolean,
    supported: Boolean,
    status: ObservationStatus,
    hasSampleableFrame: Boolean,
    consent: Boolean,
    pending: Boolean,
    sampleCount: Int,
): ObserverNextStep = when {
    !installed -> ObserverNextStep.INSTALL_GAME
    !supported -> ObserverNextStep.DIAGNOSTIC_BUILD
    status == ObservationStatus.PAUSED && sampleCount >= 32 -> ObserverNextStep.REVIEW_CALIBRATION
    status == ObservationStatus.PAUSED && hasSampleableFrame -> ObserverNextStep.SAVE_COMPARISON
    status == ObservationStatus.PAUSED -> ObserverNextStep.SOURCE_HIDDEN
    status == ObservationStatus.WAITING -> ObserverNextStep.WAIT_FOR_SOURCE
    status == ObservationStatus.OBSERVING && sampleCount >= 32 -> ObserverNextStep.REVIEW_CALIBRATION
    status == ObservationStatus.OBSERVING && hasSampleableFrame -> ObserverNextStep.SAVE_COMPARISON
    status == ObservationStatus.OBSERVING -> ObserverNextStep.WAIT_FOR_RECOGNITION
    pending -> ObserverNextStep.WAIT_FOR_PERMISSION
    !consent -> ObserverNextStep.CONSENT
    else -> ObserverNextStep.CHOOSE_SOURCE
}


/** UI-only classification of OCR evidence, never game-health truth or action authority.
 * Historical OCR can remain in diagnostics after the app becomes hidden; it must
 * not be relabelled as live when recognition misses or the clock moves backwards.
 */
internal enum class HudEvidenceState { UNKNOWN, RECENT_UNVERIFIED, HISTORICAL }

internal fun hudEvidenceState(snapshot: ObservationSnapshot, now: Long): HudEvidenceState {
    if (snapshot.status !in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED) ||
        snapshot.captureId.isNullOrBlank() || now < 0) return HudEvidenceState.UNKNOWN
    val last = snapshot.lastHealth ?: return HudEvidenceState.UNKNOWN
    if (last.observedAt < 0 || now < last.observedAt) return HudEvidenceState.UNKNOWN
    // Recent evidence requires one fully completed callback for the current frame,
    // including coherent capture/completion clocks. Displayed values alone do not
    // prove a callback happened (nor do these checks attest the selected game).
    val timing = CalibrationSamplingGate.timing(snapshot, now)
    val fresh = snapshot.status == ObservationStatus.OBSERVING &&
        snapshot.health == last.candidate && snapshot.lastRecognizedFrameAt == last.observedAt &&
        snapshot.lastFrameAt == last.observedAt &&
        snapshot.lastCompletedFrameAt == last.observedAt &&
        timing != null && timing.frameAgeMs <= 5000L
    return if (fresh) HudEvidenceState.RECENT_UNVERIFIED else HudEvidenceState.HISTORICAL
}
