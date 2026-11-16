package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Test

/** Manual synthetic states; no live game or device evaluation. */
class ShatteredManualBurningTest {
    @Test fun allTriStateCombinationsAndVersionGuards() {
        for (burning in ShatteredManualHealing.Answer.entries)
            for (flying in ShatteredManualHealing.Answer.entries)
                for (water in ShatteredManualHealing.Answer.entries)
                    for (safe in ShatteredManualHealing.Answer.entries) {
                        val expected = when {
                            burning == ShatteredManualHealing.Answer.UNKNOWN ->
                                ShatteredManualBurning.Outcome.NEEDS_CONTEXT
                            burning == ShatteredManualHealing.Answer.NO ->
                                ShatteredManualBurning.Outcome.NO_BURNING
                            flying == ShatteredManualHealing.Answer.UNKNOWN ->
                                ShatteredManualBurning.Outcome.NEEDS_CONTEXT
                            flying == ShatteredManualHealing.Answer.YES ->
                                ShatteredManualBurning.Outcome.FLYING_EXCEPTION
                            water == ShatteredManualHealing.Answer.UNKNOWN ->
                                ShatteredManualBurning.Outcome.NEEDS_CONTEXT
                            water == ShatteredManualHealing.Answer.YES ->
                                ShatteredManualBurning.Outcome.IN_WATER_MAY_EXTINGUISH
                            safe == ShatteredManualHealing.Answer.UNKNOWN ->
                                ShatteredManualBurning.Outcome.NEEDS_CONTEXT
                            safe == ShatteredManualHealing.Answer.YES ->
                                ShatteredManualBurning.Outcome.POSSIBLE_SAFE_WATER_ROUTE
                            else -> ShatteredManualBurning.Outcome.NO_CONFIRMED_SAFE_WATER
                        }
                        assertEquals(expected, ShatteredManualBurning.evaluate(
                            "4.0.2", 922L, burning, flying, water, safe))
                        assertEquals(ShatteredManualBurning.Outcome.UNSUPPORTED_VERSION,
                            ShatteredManualBurning.evaluate("4.0.1", 922L, burning, flying, water, safe))
                        assertEquals(ShatteredManualBurning.Outcome.UNSUPPORTED_VERSION,
                            ShatteredManualBurning.evaluate("4.0.2", 921L, burning, flying, water, safe))
                        assertEquals(ShatteredManualBurning.Outcome.UNSUPPORTED_VERSION,
                            ShatteredManualBurning.evaluate(null, null, burning, flying, water, safe))
                    }
    }
}
