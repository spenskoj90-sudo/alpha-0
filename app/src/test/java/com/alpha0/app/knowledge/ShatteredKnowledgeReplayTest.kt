package com.alpha0.app.knowledge

import org.junit.Assert.*
import org.junit.Test

/** Synthetic source-rule replay only. No MediaProjection/OCR/source authority,
 * installed binary certificate or real-game ground truth is claimed here. */
class ShatteredKnowledgeReplayTest {
    private val profile = KnowledgeProfile("shattered-pixel-dungeon", "android", "4.0.2",
        "local-offline-single-player", "health-potion-source-pilot-v922")
    private val raw = checkNotNull(javaClass.classLoader?.getResourceAsStream("knowledge/shattered-v4.0.2.json")).use { it.readBytes() }
    private val digest = "55ea5f25547af1bd119e2f6dbd002b73d2cb554b93e70b57838c4b3756a8f310"
    private fun pack() = KnowledgeCodec.pack(raw, digest, profile)
    private fun evaluate(signals: Map<String, Any?>) = pack().evaluate(signals, "en", 1000)

    @Test fun lowHealthAloneOrUnknownInventoryNeverRecommendsPotion() {
        for (signals in listOf(mapOf("health" to 0.1), mapOf("health" to 0.1, "no_healing" to false),
                mapOf("health" to 0.1, "known_healing_potions" to 1),
                mapOf("health" to 0.1, "no_healing" to false, "known_healing_potions" to 0))) {
            assertTrue(evaluate(signals).isEmpty())
        }
    }
    @Test fun pharmacophobiaWarnsAboutPoisonEvenWithPotionInInventory() {
        val result = evaluate(mapOf("health" to 0.1, "no_healing" to true, "known_healing_potions" to 5))
        assertEquals(listOf("pharmacophobia-poison"), result.map { it.ruleId })
        assertTrue(result.single().text.contains("poisons"))
    }
    @Test fun exactKnownChallengeAndInventoryPermitOnlyExplainedAdvisoryOption() {
        val result = evaluate(mapOf("health" to 0.2, "no_healing" to false, "known_healing_potions" to 1))
        assertEquals(listOf("known-healing-option"), result.map { it.ruleId })
        assertTrue(result.single().reason.contains("over time"))
        assertTrue(result.single().provenance.all { it.contains("57a4e06a4caf162446d1c28caa7983f0493fecf0") })
    }
    @Test fun malformedHealthOrWrongSignalTypesNeverUnlockPotion() {
        for (health in listOf<Any>(-1, 0, 1, Double.NaN, Double.POSITIVE_INFINITY, "0.1", true)) {
            assertTrue(evaluate(mapOf("health" to health, "no_healing" to false, "known_healing_potions" to 1)).isEmpty())
        }
        for (challenge in listOf<Any>("false", 0)) {
            assertTrue(evaluate(mapOf("health" to 0.1, "no_healing" to challenge, "known_healing_potions" to 1)).isEmpty())
        }
    }
    @Test fun wrongVersionProfileOrCorruptPackRejects() {
        for (wrong in listOf(profile.copy(patch = "4.0.1"), profile.copy(profile = "v921"), profile.copy(game = "other"))) {
            assertThrows(IllegalArgumentException::class.java) { KnowledgeCodec.pack(raw, digest, wrong) }
        }
        assertThrows(IllegalArgumentException::class.java) { KnowledgeCodec.pack(raw + byteArrayOf(32), digest, profile) }
    }
}
