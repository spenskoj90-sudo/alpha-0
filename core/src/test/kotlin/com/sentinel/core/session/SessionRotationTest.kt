package com.sentinel.core.session

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Duration
import java.time.Instant

class SessionRotationTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")

    @Test
    fun rotationInvalidatesOldCredentialAndIssuesNewOne() {
        val store = MemoryRotationStore()
        val manager = SessionManager(store, now = { now })
        val credential = manager.issue("device-1", Duration.ofMinutes(30))!!
        val rotator = SessionRotator(store, now = { now })
        val rotated = rotator.rotate(credential.token, Duration.ofMinutes(30))
        assertTrue(rotated is SessionRotationResult.Rotated)
        val replacement = (rotated as SessionRotationResult.Rotated).credential
        assertNotNull(replacement.token)
        assertEquals(SessionResult.Rejected(SessionFailure.REVOKED), manager.authenticate(credential.token))
        assertEquals(SessionResult.Authenticated(replacement.sessionId, "device-1"), manager.authenticate(replacement.token))
    }

    @Test
    fun rotationFailsClosedWhenAtomicStoreRejects() {
        val store = MemoryRotationStore(failRotate = true)
        val manager = SessionManager(store, now = { now })
        val credential = manager.issue("device-1", Duration.ofMinutes(30))!!
        val rotator = SessionRotator(store, now = { now })
        assertEquals(SessionRotationResult.Rejected(SessionFailure.STORE_UNAVAILABLE), rotator.rotate(credential.token, Duration.ofMinutes(30)))
        assertEquals(SessionResult.Authenticated(credential.sessionId, "device-1"), manager.authenticate(credential.token))
    }

    private class MemoryRotationStore(private val failRotate: Boolean = false) : SessionRotationStore {
        val records = mutableListOf<SessionRecord>()
        override fun save(record: SessionRecord): Boolean { records += record; return true }
        override fun findByTokenHash(tokenHash: ByteArray): SessionRecord? = records.firstOrNull { it.tokenHash.contentEquals(tokenHash) }
        override fun revoke(sessionId: String, at: Instant): Boolean {
            val index = records.indexOfFirst { it.sessionId == sessionId && it.revokedAt == null }
            if (index < 0) return false
            records[index] = records[index].copy(revokedAt = at)
            return true
        }
        override fun rotate(oldTokenHash: ByteArray, replacement: SessionRecord, revokedAt: Instant): Boolean {
            if (failRotate) return false
            val index = records.indexOfFirst { it.tokenHash.contentEquals(oldTokenHash) && it.revokedAt == null }
            if (index < 0) return false
            records[index] = records[index].copy(revokedAt = revokedAt)
            records += replacement
            return true
        }
    }
}
