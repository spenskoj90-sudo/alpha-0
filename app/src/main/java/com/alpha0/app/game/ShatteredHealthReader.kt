package com.alpha0.app.game

data class ScreenTextLine(val text: String, val left: Float, val top: Float, val right: Float, val bottom: Float)
object ShatteredHealthReader {
    private val ratio = Regex("^\\s*([0-9]{1,6})\\s*(?:\\+\\s*([0-9]{1,6})\\s*)?/\\s*([0-9]{1,6})\\s*$")

    /** Uncalibrated HUD hypothesis, never an authoritative health value or action input. */
    fun read(lines: List<ScreenTextLine>): HealthCandidate? {
        if (lines.size > 64) return null
        return lines.mapNotNull { line ->
            if (line.text.length > 64 || !listOf(line.left, line.top, line.right, line.bottom).all { it.isFinite() }) return@mapNotNull null
            if (line.left < .04f || line.right > .5f || line.top < 0f || line.bottom > .12f ||
                line.left >= line.right || line.top >= line.bottom) return@mapNotNull null
            val match = ratio.matchEntire(line.text) ?: return@mapNotNull null
            val current = match.groupValues[1].toIntOrNull() ?: return@mapNotNull null
            val shield = match.groupValues[2].toIntOrNull() ?: 0
            val maximum = match.groupValues[3].toIntOrNull() ?: return@mapNotNull null
            if (maximum <= 0 || current > maximum) return@mapNotNull null
            HealthCandidate(current, maximum, shield)
        }.singleOrNull()
    }
}
