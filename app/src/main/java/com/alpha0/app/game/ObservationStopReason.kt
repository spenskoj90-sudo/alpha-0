package com.alpha0.app.game

/** Preserve a previously latched Stop reason when service destruction merely follows stopService().
 * A still-running session destroyed unexpectedly has no trusted stop cause.
 */
internal fun observationStopReasonOnDestroy(snapshot: ObservationSnapshot): String =
    if (snapshot.status == ObservationStatus.STOPPED && snapshot.reason.isNotBlank()) {
        snapshot.reason
    } else {
        "SERVICE_DESTROYED"
    }
