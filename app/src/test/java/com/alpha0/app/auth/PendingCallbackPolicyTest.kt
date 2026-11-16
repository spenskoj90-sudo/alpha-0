package com.alpha0.app.auth

import org.junit.Assert.assertEquals
import org.junit.Test

class PendingCallbackPolicyTest {
    private val pendingState = "s".repeat(43)
    private fun classify(provider: String = "vk", operation: String = "login", state: String = pendingState) =
        PendingCallbackPolicy.classify("vk", "login", pendingState, provider, operation, state)

    @Test fun matchingCallbackIsEligibleForSingleUseConsumption() {
        assertEquals(PendingCallbackMatch.MATCH, classify())
    }

    @Test fun wrongStateProviderOrOperationMustNotConsume() {
        assertEquals(PendingCallbackMatch.STATE_MISMATCH, classify(state = "x".repeat(43)))
        assertEquals(PendingCallbackMatch.PROVIDER_MISMATCH, classify(provider = "telegram"))
        assertEquals(PendingCallbackMatch.OPERATION_MISMATCH, classify(operation = "link"))
    }

    @Test fun thousandsOfEqualLengthWrongStatesCannotMatch() {
        repeat(4096) { index ->
            val offset = index % pendingState.length
            val mutation = pendingState.substring(0, offset) +
                (if (index % 2 == 0) "X" else "Y") +
                pendingState.substring(offset + 1)
            assertEquals(PendingCallbackMatch.STATE_MISMATCH, classify(state = mutation))
        }
    }
}
