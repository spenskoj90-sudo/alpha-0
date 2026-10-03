package com.alpha0.app.game

/** Opt-in numeric comparisons only. No pixels, raw OCR or action authority. */
data class CalibrationSample(val sequence: Int, val ageMs: Long, val observed: HealthCandidate?, val current: Int, val maximum: Int)
class CalibrationCampaign {
    var count = 0; private set
    fun record(currentText: String, maximumText: String, observation: HealthObservation?, now: Long): CalibrationSample? {
        if (count >= 32 || currentText.length > 6 || maximumText.length > 6 || now < 0) return null
        if (!currentText.matches(Regex("[0-9]{1,6}")) || !maximumText.matches(Regex("[0-9]{1,6}"))) return null
        val current = currentText.toIntOrNull() ?: return null
        val maximum = maximumText.toIntOrNull() ?: return null
        if (maximum !in 1..999999 || current !in 0..maximum) return null
        val age = observation?.let { now - it.observedAt } ?: 0
        if (age !in 0..300000) return null
        return CalibrationSample(++count, age, observation?.candidate, current, maximum)
    }
}
