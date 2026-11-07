package com.alpha0.app.knowledge

import org.junit.Assert.*
import org.junit.Test

class KnowledgeFrameOrderTest {
    private val binding = TrustedKnowledgeBinding(KnowledgeFixture.profile, "source", "session", "origin")
    private fun frame(sequence: Long = 1, at: Long = 100) = TrustedKnowledgeObservation(binding, "source",
        1000 + at, mapOf("health" to 0.1), at + 10, "frame-$sequence", sequence, at, at + 10)
    @Test fun monotonicFramesAndImmutableRepeatedRenderingAreAllowed() {
        val guard = KnowledgeFrameOrder()
        assertTrue(guard.accepts(1, frame(), 110, 1000))
        assertTrue(guard.accepts(1, frame(), 111, 1000))
        assertTrue(guard.accepts(1, frame(2, 120), 130, 1000))
    }
    @Test fun sourceSessionFrameAndOcrSubstitutionsReject() {
        for (bad in listOf(frame().copy(sourceId = "foreign"),
                frame().copy(binding = binding.copy(sessionId = "foreign")),
                frame().copy(binding = binding.copy(sourceId = "other")),
                frame().copy(signals = mapOf("health" to 0.2)),
                frame().copy(frameId = "changed"), frame().copy(observedAtMs = 999),
                frame().copy(ocrCompletedMonotonicMs = 109), frame().copy(frameSequence = 0))) {
            val guard = KnowledgeFrameOrder(); assertTrue(guard.accepts(1, frame(), 110, 1000))
            assertFalse(guard.accepts(1, bad, 111, 1000))
        }
    }
    @Test fun staleFutureRollbackAndInconsistentOcrTimestampsReject() {
        for ((value, now) in listOf(frame() to 1200L, frame() to 109L,
                frame().copy(frameCapturedMonotonicMs = 111) to 120L,
                frame().copy(frameCapturedMonotonicMs = -1) to 120L)) {
            assertFalse(KnowledgeFrameOrder().accepts(1, value, now, 1000))
        }
        val guard = KnowledgeFrameOrder(); assertTrue(guard.accepts(1, frame(2, 120), 130, 1000))
        assertFalse(guard.accepts(1, frame(), 131, 1000))
        assertFalse(guard.accepts(1, frame(3, 140), 129, 1000))
        assertFalse(guard.accepts(1, frame(3, 120), 140, 1000))
    }
    @Test fun differentLeaseEpochDoesNotTransferFrameAuthority() {
        val guard = KnowledgeFrameOrder(); assertTrue(guard.accepts(1, frame(2, 120), 130, 1000))
        // The cache, not this ordering guard, separately requires a new trusted
        // lease/source/session. Clearing its epoch cannot authenticate a source.
        assertTrue(guard.accepts(2, frame(), 110, 1000))
    }
}
