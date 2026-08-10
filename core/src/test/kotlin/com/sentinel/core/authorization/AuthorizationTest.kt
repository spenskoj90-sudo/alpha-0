package com.sentinel.core.authorization

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.Instant

class AuthorizationTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")
    private val resource = Resource(type = "profile", id = "user-1")
    private val scope = ScopeRuleset(7, listOf(ScopeRule("profile", "user-1", setOf("read"))))
    private val entitlement = Entitlement("subscription", EntitlementStatus.ACTIVE, now.minusSeconds(60), now.plusSeconds(3600))

    private fun request(
        identityId: String = "device-1",
        roles: Set<String> = setOf("member"),
        requiredRole: String = "member",
        permissions: Set<String> = setOf("profile:read"),
        requestScope: ScopeRuleset = scope,
        requestEntitlement: Entitlement = entitlement,
        policy: Policy = Policy { true },
        context: AuthorizationContext = AuthorizationContext()
    ) = AuthorizationRequest(identityId, roles, requiredRole, permissions, requestScope, requestEntitlement, policy, context, "read", resource, now)

    @Test fun validRequestIsAllowedAndPreservesScopeVersion() = assertEquals(AuthorizationDecision.Allow(7), AuthorizationEngine.decide(request()))
    @Test fun blankIdentityIsDenied() = assertEquals(AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY), AuthorizationEngine.decide(request(identityId = "")))
    @Test fun missingRequiredRoleIsDenied() = assertEquals(AuthorizationDecision.Deny(DenyReason.MISSING_ROLE), AuthorizationEngine.decide(request(roles = setOf("viewer"))))
    @Test fun missingPermissionIsDenied() = assertEquals(AuthorizationDecision.Deny(DenyReason.MISSING_PERMISSION), AuthorizationEngine.decide(request(permissions = emptySet())))
    @Test fun wrongScopeIsDenied() {
        val wrongScope = ScopeRuleset(8, listOf(ScopeRule("profile", "user-2", setOf("read"))))
        assertEquals(AuthorizationDecision.Deny(DenyReason.SCOPE_DENIED), AuthorizationEngine.decide(request(requestScope = wrongScope)))
    }
    @Test fun invalidScopeDefinitionIsDeniedAsMalformedRequest() {
        val invalidScope = ScopeRuleset(0, listOf(ScopeRule("profile", "user-1", setOf("read"))))
        assertEquals(AuthorizationDecision.Deny(DenyReason.MALFORMED_REQUEST), AuthorizationEngine.decide(request(requestScope = invalidScope)))
    }
    @Test fun expiredEntitlementIsDenied() {
        val expired = entitlement.copy(status = EntitlementStatus.EXPIRED, expiresAt = now.minusSeconds(1))
        assertEquals(AuthorizationDecision.Deny(DenyReason.ENTITLEMENT_DENIED), AuthorizationEngine.decide(request(requestEntitlement = expired)))
    }
    @Test fun entitlementWithReversedTimeWindowIsMalformed() {
        val invalid = entitlement.copy(startsAt = now.plusSeconds(60), expiresAt = now.minusSeconds(60))
        assertEquals(AuthorizationDecision.Deny(DenyReason.MALFORMED_REQUEST), AuthorizationEngine.decide(request(requestEntitlement = invalid)))
    }
    @Test fun policyDenialIsEnforced() = assertEquals(AuthorizationDecision.Deny(DenyReason.POLICY_DENIED), AuthorizationEngine.decide(request(policy = Policy { false })))
    @Test fun policyFailureFailsClosed() = assertEquals(AuthorizationDecision.Deny(DenyReason.POLICY_DENIED), AuthorizationEngine.decide(request(policy = Policy { error("policy failure") })))
    @Test fun malformedContextIsDenied() = assertEquals(AuthorizationDecision.Deny(DenyReason.CONTEXT_DENIED), AuthorizationEngine.decide(request(context = AuthorizationContext(mapOf("region" to "")))))
    @Test fun expirationBoundaryIsDenied() = assertEquals(AuthorizationDecision.Deny(DenyReason.ENTITLEMENT_DENIED), AuthorizationEngine.decide(request(requestEntitlement = entitlement.copy(expiresAt = now))))

    @Test fun oversizedRoleSetIsRejectedBeforePolicyEvaluation() {
        val oversizedRoles = (0..128).map { "role-$it" }.toSet() + "member"
        assertEquals(AuthorizationDecision.Deny(DenyReason.MALFORMED_REQUEST), AuthorizationEngine.decide(request(roles = oversizedRoles)))
    }

    @Test fun oversizedContextIsDenied() {
        val oversized = (0..64).associate { "key-$it" to "value" }
        assertEquals(AuthorizationDecision.Deny(DenyReason.CONTEXT_DENIED), AuthorizationEngine.decide(request(context = AuthorizationContext(oversized))))
    }

    @Test fun oversizedIdentityIsDenied() {
        assertEquals(AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY), AuthorizationEngine.decide(request(identityId = "x".repeat(257))))
    }
}
