package com.sentinel.core.authorization

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import com.sentinel.core.session.SessionManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Duration
import java.time.Instant

class AuthorizationMiddlewareTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")

    @Test
    fun validSessionAndProfileAllow() {
        val store = MemorySessionStore()
        val sessions = SessionManager(store, now = { now })
        val credential = sessions.issue("device-1", Duration.ofMinutes(10))!!
        val profile = AuthorizationProfile(
            roles = setOf("operator"), requiredRole = "operator", permissions = setOf("report:read"),
            scope = ScopeRuleset(1, listOf(ScopeRule("report", null, setOf("read")))),
            entitlement = Entitlement("license", EntitlementStatus.ACTIVE, now.minusSeconds(1), now.plusSeconds(60)),
            policy = Policy { true }
        )
        val middleware = AuthorizationMiddleware(sessions, AuthorizationProfileStore { profile }, now = { now })
        assertTrue(middleware.authorize(credential.token, "read", Resource("report", "r1")) is ProtectedAuthorizationResult.Allow)
    }

    @Test
    fun missingProfileDenies() {
        val sessions = SessionManager(MemorySessionStore(), now = { now })
        val credential = sessions.issue("device-1", Duration.ofMinutes(10))!!
        val middleware = AuthorizationMiddleware(sessions, AuthorizationProfileStore { null }, now = { now })
        assertEquals(ProtectedAuthorizationResult.Deny(403, "forbidden"), middleware.authorize(credential.token, "read", Resource("report", "r1")))
    }

    @Test
    fun clientCannotSupplyAuthorizationAttributes() {
        val sessions = SessionManager(MemorySessionStore(), now = { now })
        val credential = sessions.issue("device-1", Duration.ofMinutes(10))!!
        val profile = AuthorizationProfile(
            roles = setOf("viewer"), requiredRole = "operator", permissions = setOf("report:read"),
            scope = ScopeRuleset(1, listOf(ScopeRule("report", null, setOf("read")))),
            entitlement = Entitlement("license", EntitlementStatus.ACTIVE, now.minusSeconds(1), null), policy = Policy { true }
        )
        val middleware = AuthorizationMiddleware(sessions, AuthorizationProfileStore { profile }, now = { now })
        assertEquals(ProtectedAuthorizationResult.Deny(403, "missing_role"), middleware.authorize(credential.token, "read", Resource("report", "r1")))
    }

    @Test
    fun auditFailureFailsClosed() {
        val sessions = SessionManager(MemorySessionStore(), now = { now })
        val credential = sessions.issue("device-1", Duration.ofMinutes(10))!!
        val profile = AuthorizationProfile(
            roles = setOf("operator"), requiredRole = "operator", permissions = setOf("report:read"),
            scope = ScopeRuleset(1, listOf(ScopeRule("report", null, setOf("read")))),
            entitlement = Entitlement("license", EntitlementStatus.ACTIVE, now.minusSeconds(1), null), policy = Policy { true }
        )
        val sink = AuditSink { false }
        val middleware = AuthorizationMiddleware(sessions, AuthorizationProfileStore { profile }, now = { now }, auditSink = sink)
        assertEquals(ProtectedAuthorizationResult.Deny(503, "audit_unavailable"), middleware.authorize(credential.token, "read", Resource("report", "r1")))
    }

    @Test
    fun denyDecisionIsAudited() {
        val sessions = SessionManager(MemorySessionStore(), now = { now })
        val credential = sessions.issue("device-1", Duration.ofMinutes(10))!!
        val profile = AuthorizationProfile(
            roles = setOf("viewer"), requiredRole = "operator", permissions = emptySet(),
            scope = ScopeRuleset(1, listOf(ScopeRule("report", null, setOf("read")))),
            entitlement = Entitlement("license", EntitlementStatus.ACTIVE, now.minusSeconds(1), null), policy = Policy { true }
        )
        val events = mutableListOf<AuditEvent>()
        val sink = AuditSink { event -> events += event; true }
        val middleware = AuthorizationMiddleware(sessions, AuthorizationProfileStore { profile }, now = { now }, auditSink = sink)
        assertEquals(ProtectedAuthorizationResult.Deny(403, "missing_role"), middleware.authorize(credential.token, "read", Resource("report", "r1")))
        assertEquals("DENY", events.single().outcome)
        assertTrue(events.single().reason!!.contains("missing_role"))
    }

    private class MemorySessionStore : com.sentinel.core.session.SessionStore {
        private val records = mutableListOf<com.sentinel.core.session.SessionRecord>()
        override fun save(record: com.sentinel.core.session.SessionRecord): Boolean { records += record; return true }
        override fun findByTokenHash(tokenHash: ByteArray) = records.firstOrNull { it.tokenHash.contentEquals(tokenHash) }
        override fun revoke(sessionId: String, at: Instant): Boolean = true
    }
}
