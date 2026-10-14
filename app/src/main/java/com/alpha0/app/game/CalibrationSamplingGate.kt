package com.alpha0.app.game

/** The opt-in sample must belong to the presently observing, unchanged installed game.
 * An old OCR candidate can remain visible for explanatory diagnostics but cannot count
 * as the observation of a newer pending/missed frame or a paused capture.
 * This is a metadata and freshness fence only, never proof of screen/game provenance.
 */
internal object CalibrationSamplingGate {
    fun canSample(snapshot: ObservationSnapshot, captured: StockGameInstall?, installed: StockGameInstall?): Boolean =
        snapshot.status == ObservationStatus.OBSERVING && captured != null && captured == installed

    fun current(snapshot: ObservationSnapshot): HealthObservation? {
        if (snapshot.status != ObservationStatus.OBSERVING) return null
        val last = snapshot.lastHealth ?: return null
        return last.takeIf {
            snapshot.health == last.candidate && snapshot.lastFrameAt == last.observedAt
        }
    }
}
