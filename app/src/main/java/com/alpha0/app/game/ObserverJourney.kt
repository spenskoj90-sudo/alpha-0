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
