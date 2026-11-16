package com.alpha0.app.auth

import java.security.MessageDigest

internal enum class PendingCallbackMatch {
    MATCH, OPERATION_MISMATCH, PROVIDER_MISMATCH, STATE_MISMATCH,
}

/** Only an exact pending-flow match may authorize single-use PKCE consumption. */
internal object PendingCallbackPolicy {
    fun classify(
        pendingProvider: String,
        pendingOperation: String,
        pendingState: String,
        callbackProvider: String,
        callbackOperation: String,
        callbackState: String,
    ): PendingCallbackMatch = when {
        pendingOperation != callbackOperation -> PendingCallbackMatch.OPERATION_MISMATCH
        pendingProvider != callbackProvider -> PendingCallbackMatch.PROVIDER_MISMATCH
        !MessageDigest.isEqual(
            pendingState.toByteArray(Charsets.UTF_8),
            callbackState.toByteArray(Charsets.UTF_8),
        ) -> PendingCallbackMatch.STATE_MISMATCH
        else -> PendingCallbackMatch.MATCH
    }
}
