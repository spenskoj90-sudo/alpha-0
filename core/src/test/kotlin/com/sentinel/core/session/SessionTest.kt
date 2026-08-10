package com.sentinel.core.session

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.security.SecureRandom
import java.time.Duration
import java.time.Instant

class SessionTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")

    @Test
    fun issuedSessionAuthenticates() {
        val store = MemorySessionStore()
        val manager = SessionManager(store, SecureRandom(), { now })
        val credential = manager.issue("device-1", Duration.ofMinutes(30))
        assertNotNull(credential)
        val result = manager.authenticate(credential!!.token)
        assertEquals(SessionResult.Authenticated(credential.sessionId, "device-1"), result)
        assertEquals(32, store.records.single().tokenHash.size)
        assertTrue(!store.records.single().tokenHash.contentEquals(credential.token.toByteArray()))
    }

    @Test
    fun expiredSessionIsRejected() {
        val store = MemorySessionStore()
        var current = now
        val manager = SessionManager(store, SecureRandom(), { current })
        val credential = manager.issue("device-1", Duration.ofMinutes(1))!!
        current = now.plusSeconds(61)
        assertEquals(SessionResult.Rejected(SessionFailure.EXPIRED), manager.authenticate(credential.token))
    }

    @Test
    fun revokedSessionIsRejected() {
        val store = MemorySessionStore()
        val manager = SessionManager(store, SecureRandom(), { now })
        val credential = manager.issue("device-1", Duration.ofMinutes(30))!!
        assertTrue(manager.revoke(credential.sessionId))
        assertEquals(SessionResult.Rejected(SessionFailure.REVOKED), manager.authenticate(credential.token))
    }

    @Test
    fun malformedTokenIsRejected() {
        val manager = SessionManager(MemorySessionStore(), SecureRandom(), { now })
        assertEquals(SessionResult.Rejected(SessionFailure.MALFORMED_REQUEST), manager.authenticate("not-a-token"))
    }

    @Test
    fun oversizedLifetimeIsRejected() {
        val manager = SessionManager(MemorySessionStore(), SecureRandom(), { now })
        assertTrue(manager.issue("device-1", Duration.ofDays(31)) == null)
    }

    @Test
    fun storeFailureFailsClosed() {
        val store = object : SessionStore {
            override fun save(record: SessionRecord): Boolean = false
            override fun findByTokenHash(tokenHash: ByteArray): SessionRecord? = error("db unavailable")
            override fun revoke(sessionId: String, at: Instant): Boolean = error("db unavailable")
        }
        val manager = SessionManager(store, SecureRandom(), { now })
        assertTrue(manager.issue("device-1", Duration.ofMinutes(30)) == null)
        assertEquals(SessionResult.Rejected(SessionFailure.STORE_UNAVAILABLE), manager.authenticate("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))
        assertTrue(!manager.revoke("session-1"))
    }

    private class MemorySessionStore : SessionStore {
        val records = mutableListOf<SessionRecord>()
        override fun save(record: SessionRecord): Boolean {
            if (records.any { it.sessionId == record.sessionId || it.tokenHash.contentEquals(record.tokenHash) }) return false
            records += record
            return true
        }

        override fun findByTokenHash(tokenHash: ByteArray): SessionRecord? =
            records.firstOrNull { it.tokenHash.contentEquals(tokenHash) }

        override fun revoke(sessionId: String, at: Instant): Boolean {
            val index = records.indexOfFirst { it.sessionId == sessionId && it.revokedAt == null }
            if (index < 0) return false
            records[index] = records[index].copy(revokedAt = at)
            return true
        }
    }
}
