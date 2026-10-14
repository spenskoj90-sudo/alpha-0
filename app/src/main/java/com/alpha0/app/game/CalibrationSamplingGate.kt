package com.alpha0.app.game

/** The opt-in sample must belong to an unchanged installed game and a current
 * capture session. A paused single-phone comparison may use only the last
 * COMPLETED OCR frame; its actual age is recorded and stale rows count as stale.
 * This is metadata/freshness fencing, not screen-source or game attestation.
 */
internal object CalibrationSamplingGate {
    fun canSample(snapshot: ObservationSnapshot, captured: StockGameInstall?, installed: StockGameInstall?): Boolean =
        snapshot.status in setOf(ObservationStatus.OBSERVING, ObservationStatus.PAUSED) &&
            captured != null && captured == installed

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
