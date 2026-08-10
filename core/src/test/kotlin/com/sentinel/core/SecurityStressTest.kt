package com.sentinel.core

import com.sentinel.core.authorization.*
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import kotlin.system.measureTimeMillis

class SecurityStressTest {
    @Test
    fun authorizationHandlesBoundedRepeatedEvaluation() {
        val now = Instant.parse("2026-08-10T12:00:00Z")
        val request = AuthorizationRequest(
            identityId = "device-1",
            roles = setOf("operator"),
            requiredRole = "operator",
            permissions = setOf("protected:read"),
            scope = ScopeRuleset(1, listOf(ScopeRule("protected", null, setOf("read")))),
            entitlement = Entitlement("stress", EntitlementStatus.ACTIVE, now.minusSeconds(1), now.plusSeconds(3600)),
            policy = Policy { true },
            context = AuthorizationContext(mapOf("tenant" to "stress")),
            action = "read",
            resource = Resource("protected", "item"),
            now = now
        )
        val elapsed = measureTimeMillis { repeat(10_000) { assertTrue(AuthorizationEngine.decide(request) is AuthorizationDecision.Allow) } }
        assertTrue("authorization stress run exceeded 5s: ${elapsed}ms", elapsed < 5000)
    }

    @Test
    fun malformedInputFailsClosedUnderRepetition() {
        val now = Instant.parse("2026-08-10T12:00:00Z")
        val base = AuthorizationRequest(
            identityId = "device-1", roles = setOf("operator"), requiredRole = "operator", permissions = setOf("protected:read"),
            scope = ScopeRuleset(1, listOf(ScopeRule("protected", null, setOf("read")))),
            entitlement = Entitlement("stress", EntitlementStatus.ACTIVE, now.minusSeconds(1), now.plusSeconds(3600)),
            policy = Policy { true }, context = AuthorizationContext(), action = "read", resource = Resource("protected", "item"), now = now
        )
        repeat(10_000) {
            val decision = AuthorizationEngine.decide(base.copy(identityId = ""))
            assertTrue(decision == AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY))
        }
    }
}
