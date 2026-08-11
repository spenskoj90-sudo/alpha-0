package com.sentinel.core.session

import java.security.MessageDigest
import java.security.SecureRandom
import java.time.Duration
import java.time.Instant
import java.util.Base64

/** Atomic session rotation boundary. Implementations must revoke the old token and persist the new token in one transaction. */
interface SessionRotationStore : SessionStore {
    fun rotate(oldTokenHash: ByteArray, replacement: SessionRecord, revokedAt: Instant): Boolean
}

sealed interface SessionRotationResult {
    data class Rotated(val credential: SessionCredential) : SessionRotationResult
    data class Rejected(val reason: SessionFailure) : SessionRotationResult
}

class SessionRotator(
    private val store: SessionRotationStore,
    private val random: SecureRandom = SecureRandom(),
    private val now: () -> Instant = Instant::now
) {
    fun rotate(token: String, lifetime: Duration): SessionRotationResult {
        if (token.isBlank() || token.length > MAX_TOKEN_LENGTH || lifetime.isNegative || lifetime.isZero || lifetime > MAX_LIFETIME) {
            return SessionRotationResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        }
        val raw = try { Base64.getUrlDecoder().decode(token) } catch (_: IllegalArgumentException) {
            return SessionRotationResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        }
        if (raw.size != TOKEN_BYTES) return SessionRotationResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        val oldHash = sha256(raw)
        val existing = try { store.findByTokenHash(oldHash) } catch (_: Exception) {
            return SessionRotationResult.Rejected(SessionFailure.STORE_UNAVAILABLE)
        } ?: return SessionRotationResult.Rejected(SessionFailure.NOT_FOUND)
        val current = now()
        if (existing.revokedAt != null) return SessionRotationResult.Rejected(SessionFailure.REVOKED)
        if (!current.isBefore(existing.expiresAt)) return SessionRotationResult.Rejected(SessionFailure.EXPIRED)

        val newRaw = ByteArray(TOKEN_BYTES).also(random::nextBytes)
        val credentialToken = Base64.getUrlEncoder().withoutPadding().encodeToString(newRaw)
        val sessionId = Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(SESSION_ID_BYTES).also(random::nextBytes))
        val expiresAt = current.plus(lifetime)
        val replacement = SessionRecord(sessionId, existing.subjectId, sha256(newRaw), expiresAt)
        return try {
            if (!store.rotate(oldHash, replacement, current)) SessionRotationResult.Rejected(SessionFailure.STORE_UNAVAILABLE)
            else SessionRotationResult.Rotated(SessionCredential(sessionId, credentialToken, expiresAt))
        } catch (_: Exception) {
            SessionRotationResult.Rejected(SessionFailure.STORE_UNAVAILABLE)
        }
    }

    private fun sha256(value: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(value)

    private companion object {
        const val TOKEN_BYTES = 32
        const val SESSION_ID_BYTES = 16
        const val MAX_TOKEN_LENGTH = 256
        val MAX_LIFETIME: Duration = Duration.ofDays(30)
    }
}
