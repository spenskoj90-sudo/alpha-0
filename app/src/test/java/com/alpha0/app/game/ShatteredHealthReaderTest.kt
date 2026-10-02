package com.alpha0.app.game

import org.junit.Assert.*
import org.junit.Test

class ShatteredHealthReaderTest {
    @Test fun `only a valid ratio in the upper left HUD is a candidate`() {
        assertEquals(HealthCandidate(4, 20, 0), ShatteredHealthReader.read(listOf(line("4 / 20"))))
        assertNull(ShatteredHealthReader.read(listOf(line("4/20", top = .5f))))
        assertNull(ShatteredHealthReader.read(listOf(line("4/20", left = .7f))))
        assertNull(ShatteredHealthReader.read(listOf(line("HP unknown"))))
    }

    @Test fun `shield is retained separately and never mistaken for current health`() {
        assertEquals(HealthCandidate(4, 20, 8), ShatteredHealthReader.read(listOf(line("4+8/20"))))
        assertEquals(HealthCandidate(0, 20, 0), ShatteredHealthReader.read(listOf(line("0/20"))))
    }

    @Test fun `malformed impossible and ambiguous ratios remain unknown`() {
        listOf("21/20", "4/0", "-4/20", "4/20 xp", "999999999999/20", "4//20", "4/20/30")
            .forEach { assertNull(it, ShatteredHealthReader.read(listOf(line(it)))) }
        assertNull(ShatteredHealthReader.read(listOf(line("4/20"), line("3/10"))))
    }

    private fun line(text: String, left: Float = .1f, top: Float = .01f) =
        ScreenTextLine(text, left, top, left + .15f, top + .02f)
}
