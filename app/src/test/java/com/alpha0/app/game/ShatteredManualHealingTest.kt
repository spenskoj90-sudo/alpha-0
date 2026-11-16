package com.alpha0.app.game

import org.junit.Assert.assertEquals
import org.junit.Test

/** Manually entered facts are not trusted frame observations. */
class ShatteredManualHealingTest {
    @Test fun allThreeStateCombinationsFailClosedExceptExplicitRules() {
        for (low in ShatteredManualHealing.Answer.entries) for (pharma in ShatteredManualHealing.Answer.entries) for (potion in ShatteredManualHealing.Answer.entries) {
            val expected = when {
                pharma == ShatteredManualHealing.Answer.YES -> ShatteredManualHealing.Outcome.POISON_WARNING
                low == ShatteredManualHealing.Answer.UNKNOWN || pharma == ShatteredManualHealing.Answer.UNKNOWN || potion == ShatteredManualHealing.Answer.UNKNOWN -> ShatteredManualHealing.Outcome.NEEDS_CONTEXT
                low == ShatteredManualHealing.Answer.YES && pharma == ShatteredManualHealing.Answer.NO && potion == ShatteredManualHealing.Answer.YES -> ShatteredManualHealing.Outcome.POSSIBLE_OPTION
                else -> ShatteredManualHealing.Outcome.NO_RULE_MATCH
            }
            assertEquals("low=$low pharma=$pharma potion=$potion", expected,
                ShatteredManualHealing.evaluate("4.0.2", 922L, low, pharma, potion))
            assertEquals(ShatteredManualHealing.Outcome.UNSUPPORTED_VERSION,
                ShatteredManualHealing.evaluate("4.0.1", 922L, low, pharma, potion))
            assertEquals(ShatteredManualHealing.Outcome.UNSUPPORTED_VERSION,
                ShatteredManualHealing.evaluate("4.0.2", 921L, low, pharma, potion))
        }
    }

    @Test fun emptyVersionAndAllUnknownNeverGiveActionableAdvice() {
        assertEquals(ShatteredManualHealing.Outcome.UNSUPPORTED_VERSION,
            ShatteredManualHealing.evaluate(null, null, ShatteredManualHealing.Answer.YES, ShatteredManualHealing.Answer.NO, ShatteredManualHealing.Answer.YES))
        assertEquals(ShatteredManualHealing.Outcome.NEEDS_CONTEXT,
            ShatteredManualHealing.evaluate("4.0.2", 922, ShatteredManualHealing.Answer.UNKNOWN, ShatteredManualHealing.Answer.UNKNOWN, ShatteredManualHealing.Answer.UNKNOWN))
        assertEquals(ShatteredManualHealing.Outcome.NO_RULE_MATCH,
            ShatteredManualHealing.evaluate("4.0.2", 922, ShatteredManualHealing.Answer.YES, ShatteredManualHealing.Answer.NO, ShatteredManualHealing.Answer.NO))
    }
}
