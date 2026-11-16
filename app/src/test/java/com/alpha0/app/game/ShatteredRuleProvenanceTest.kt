package com.alpha0.app.game

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class ShatteredRuleProvenanceTest {
    @Test fun `manual rule source supports only exact 4_0_2 release build`() {
        assertTrue(ShatteredRuleProvenance.supports("4.0.2", 922L))
        assertFalse(ShatteredRuleProvenance.supports("4.0.2", 921L))
        assertFalse(ShatteredRuleProvenance.supports("4.0.3", 923L))
        assertFalse(ShatteredRuleProvenance.supports(null, null))
        assertTrue(Regex("[0-9a-f]{40}").matches(ShatteredRuleProvenance.SOURCE_COMMIT))
        assertTrue(ShatteredRuleProvenance.HEALING_SOURCE.contains("/blob/" + ShatteredRuleProvenance.SOURCE_COMMIT + "/"))
        assertTrue(ShatteredRuleProvenance.BURNING_SOURCE.contains("/blob/" + ShatteredRuleProvenance.SOURCE_COMMIT + "/"))
        assertFalse(ShatteredRuleProvenance.HEALING_SOURCE.contains("/blob/v4.0.2/"))
    }

    @Test fun `manual outcomes cannot be reused on unreviewed future version`() {
        val yes = ShatteredManualHealing.Answer.YES
        val no = ShatteredManualHealing.Answer.NO
        assertEquals(ShatteredManualHealing.Outcome.POSSIBLE_OPTION,
            ShatteredManualHealing.evaluate("4.0.2", 922L, yes, no, yes))
        assertEquals(ShatteredManualHealing.Outcome.UNSUPPORTED_VERSION,
            ShatteredManualHealing.evaluate("4.0.3", 923L, yes, no, yes))
        assertEquals(ShatteredManualBurning.Outcome.UNSUPPORTED_VERSION,
            ShatteredManualBurning.evaluate("4.0.3", 923L, yes, no, yes, yes))
    }
}
