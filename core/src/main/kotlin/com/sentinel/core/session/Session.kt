package com.sentinel.core.session

import java.security.MessageDigest
import java.security.SecureRandom
import java.time.Instant
import java.time.Duration
import java.util.Base64

/**
 * Opaque session credentials for server-side sessions.
 * Raw credentials are returned only at issuance time; persistence stores only
 * a SHA-256 digest so a database read does not directly reveal bearer tokens.
 */
data class SessionRecord(
    val sessionId: String,
    val subjectId: String,
    val tokenHash: ByteArray,
    val expiresAt: Instant,
    val revokedAt: Instant? = null
)

data class SessionCredential(
    val sessionId: String,
    val token: String,
    val expiresAt: Instant
)

enum class SessionFailure {
    MALFORMED_REQUEST,
    NOT_FOUND,
    EXPIRED,
    REVOKED,
    STORE_UNAVAILABLE
}

sealed interface SessionResult {
    data class Authenticated(val sessionId: String, val subjectId: String) : SessionResult
    data class Rejected(val reason: SessionFailure) : SessionResult
}

interface SessionStore {
    fun save(record: SessionRecord): Boolean
    fun findByTokenHash(tokenHash: ByteArray): SessionRecord?
    fun revoke(sessionId: String, at: Instant): Boolean
}

class SessionManager(
    private val store: SessionStore,
    private val random: SecureRandom = SecureRandom(),
    private val now: () -> Instant = Instant::now
) {
    fun issue(subjectId: String, lifetime: Duration): SessionCredential? {
        if (subjectId.isBlank() || subjectId.length > MAX_SUBJECT_LENGTH) return null
        if (lifetime.isNegative || lifetime.isZero || lifetime > MAX_LIFETIME) return null

        val raw = ByteArray(TOKEN_BYTES).also(random::nextBytes)
        val token = Base64.getUrlEncoder().withoutPadding().encodeToString(raw)
        val sessionId = Base64.getUrlEncoder().withoutPadding().encodeToString(
            ByteArray(SESSION_ID_BYTES).also(random::nextBytes)
        )
        val expiresAt = now().plus(lifetime)
        val record = SessionRecord(sessionId, subjectId, sha256(raw), expiresAt)

        return try {
            if (!store.save(record)) null
            else SessionCredential(sessionId, token, expiresAt)
        } catch (_: Exception) {
            null
        }
    }

    fun authenticate(token: String): SessionResult {
        if (token.isBlank() || token.length > MAX_TOKEN_LENGTH) {
            return SessionResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        }

        val raw = try {
            Base64.getUrlDecoder().decode(token)
        } catch (_: IllegalArgumentException) {
            return SessionResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        }
        if (raw.size != TOKEN_BYTES) return SessionResult.Rejected(SessionFailure.MALFORMED_REQUEST)

        val record = try {
            store.findByTokenHash(sha256(raw))
        } catch (_: Exception) {
            return SessionResult.Rejected(SessionFailure.STORE_UNAVAILABLE)
        } ?: return SessionResult.Rejected(SessionFailure.NOT_FOUND)

        val current = now()
        if (record.revokedAt != null) return SessionResult.Rejected(SessionFailure.REVOKED)
        if (!current.isBefore(record.expiresAt)) return SessionResult.Rejected(SessionFailure.EXPIRED)
        if (record.subjectId.isBlank() || record.sessionId.isBlank()) {
            return SessionResult.Rejected(SessionFailure.MALFORMED_REQUEST)
        }
        return SessionResult.Authenticated(record.sessionId, record.subjectId)
    }

    fun revoke(sessionId: String): Boolean {
        if (sessionId.isBlank() || sessionId.length > MAX_SESSION_ID_LENGTH) return false
        return try { store.revoke(sessionId, now()) } catch (_: Exception) { false }
    }

    private fun sha256(value: ByteArray): ByteArray =
        MessageDigest.getInstance("SHA-256").digest(value)

    private companion object {
        const val TOKEN_BYTES = 32
        const val SESSION_ID_BYTES = 16
        const val MAX_TOKEN_LENGTH = 256
        const val MAX_SESSION_ID_LENGTH = 128
        const val MAX_SUBJECT_LENGTH = 256
        val MAX_LIFETIME: Duration = Duration.ofDays(30)
    }
}
