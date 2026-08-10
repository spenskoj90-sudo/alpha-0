package com.sentinel.core.authorization

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.Instant

class AuthorizationTest {

    private val now = Instant.parse("2026-08-10T12:00:00Z")
    private val resource = Resource(type = "profile", id = "user-1")
    private val scope = ScopeRuleset(
        version = 7,
        rules = listOf(
            ScopeRule(
                resourceType = "profile",
                resourceId = "user-1",
                actions = setOf("read")
            )
        )
    )
    private val entitlement = Entitlement(
        source = "subscription",
        status = EntitlementStatus.ACTIVE,
        startsAt = now.minusSeconds(60),
        expiresAt = now.plusSeconds(3600)
    )

    private fun request(
        identityId: String = "device-1",
        roles: Set<String> = setOf("member"),
        requiredRole: String = "member",
        permissions: Set<String> = setOf("profile:read"),
        requestScope: ScopeRuleset = scope,
        requestEntitlement: Entitlement = entitlement,
        policy: Policy = Policy { true },
        context: AuthorizationContext = AuthorizationContext()
    ) = AuthorizationRequest(
        identityId = identityId,
        roles = roles,
        requiredRole = requiredRole,
        permissions = permissions,
        scope = requestScope,
        entitlement = requestEntitlement,
        policy = policy,
        context = context,
        action = "read",
        resource = resource,
        now = now
    )

    @Test
    fun validRequestIsAllowedAndPreservesScopeVersion() {
        assertEquals(
            AuthorizationDecision.Allow(scopeVersion = 7),
            AuthorizationEngine.decide(request())
        )
    }

    @Test
    fun blankIdentityIsDenied() {
        assertEquals(
            AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY),
            AuthorizationEngine.decide(request(identityId = ""))
        )
    }

    @Test
    fun missingRequiredRoleIsDenied() {
        assertEquals(
            AuthorizationDecision.Deny(DenyReason.MISSING_ROLE),
            AuthorizationEngine.decide(request(roles = setOf("viewer")))
        )
    }

    @Test
    fun missingPermissionIsDenied() {
        assertEquals(
            AuthorizationDecision.Deny(DenyReason.MISSING_PERMISSION),
            AuthorizationEngine.decide(request(permissions = emptySet()))
        )
    }

    @Test
    fun wrongScopeIsDenied() {
        val wrongScope = ScopeRuleset(
            version = 8,
            rules = listOf(
                ScopeRule("profile", "user-2", setOf("read"))
            )
        )

        assertEquals(
            AuthorizationDecision.Deny(DenyReason.SCOPE_DENIED),
            AuthorizationEngine.decide(request(requestScope = wrongScope))
        )
    }

    @Test
    fun expiredEntitlementIsDenied() {
        val expired = entitlement.copy(
            status = EntitlementStatus.EXPIRED,
            expiresAt = now.minusSeconds(1)
        )

        assertEquals(
            AuthorizationDecision.Deny(DenyReason.ENTITLEMENT_DENIED),
            AuthorizationEngine.decide(request(requestEntitlement = expired))
        )
    }

    @Test
    fun policyDenialIsEnforced() {
        assertEquals(
            AuthorizationDecision.Deny(DenyReason.POLICY_DENIED),
            AuthorizationEngine.decide(request(policy = Policy { false }))
        )
    }

    @Test
    fun malformedContextIsDenied() {
        assertEquals(
            AuthorizationDecision.Deny(DenyReason.CONTEXT_DENIED),
            AuthorizationEngine.decide(
                request(context = AuthorizationContext(mapOf("region" to "")))
            )
        )
    }
}
