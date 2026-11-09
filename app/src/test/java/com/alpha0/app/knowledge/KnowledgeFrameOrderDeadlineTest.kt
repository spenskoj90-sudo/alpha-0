package com.alpha0.app.knowledge

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Service-owned OCR completion must not bypass the processing deadline. */
class KnowledgeFrameOrderDeadlineTest {
    private fun frame(completedAtMs: Long) = TrustedKnowledgeObservation(
        TrustedKnowledgeBinding(KnowledgeFixture.profile, "source", "session", "fixture-origin", KnowledgeFixture.target),
        "source", 1500, mapOf("health" to 0.2), completedAtMs,
        "frame-1", 1, 10, completedAtMs
    )

    @Test fun completionAtFiveSecondsIsAccepted() {
        val order = KnowledgeFrameOrder()
        assertTrue(order.processing(1, 1, 10, 10, 30000))
        assertTrue(order.accepts(1, frame(5010), 5010, 30000))
        assertFalse(order.isBlocked(1))
    }

    @Test fun lateCompletionWithoutAnotherProcessingPollLatchesUnavailable() {
        val order = KnowledgeFrameOrder()
        assertTrue(order.processing(1, 1, 10, 10, 30000))
        // Under the pack's 30-second state age, but beyond OCR's five-second bound.
        assertFalse(order.accepts(1, frame(5011), 5011, 30000))
        assertTrue(order.isBlocked(1))
        assertFalse(order.accepts(1, frame(5010), 5011, 30000))
    }

    @Test fun tighterPackAgeStillBlocksCompletion() {
        val order = KnowledgeFrameOrder()
        assertTrue(order.processing(1, 1, 10, 10, 100))
        assertFalse(order.accepts(1, frame(111), 111, 100))
        assertTrue(order.isBlocked(1))
    }
}
