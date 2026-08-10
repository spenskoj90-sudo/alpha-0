package com.sentinel.core.authorization

import java.time.Instant

/**
 * Deterministic authorization domain for Sentinel Core.
 *
 * This module intentionally contains no transport, persistence, billing, or UI code.
 * The server/API adapter must invoke this engine before protected operations are executed.
 */

data class Resource(
    val type: String,
    val id: String
)

data class ScopeRule(
    val resourceType: String,
    val resourceId: String? = null,
    val actions: Set<String>
) {
    fun permits(action: String, resource: Resource): Boolean =
        action in actions &&
            resourceType == resource.type &&
            (resourceId == null || resourceId == resource.id)
}

data class ScopeRuleset(
    val version: Int,
    val rules: List<ScopeRule>
) {
    fun permits(action: String, resource: Resource): Boolean =
        rules.any { it.permits(action, resource) }
}

enum class EntitlementStatus {
    ACTIVE,
    EXPIRED,
    REVOKED,
    SUSPENDED
}

data class Entitlement(
    val source: String,
    val status: EntitlementStatus,
    val startsAt: Instant,
    val expiresAt: Instant?
) {
    fun isActiveAt(now: Instant): Boolean =
        status == EntitlementStatus.ACTIVE &&
            !now.isBefore(startsAt) &&
            (expiresAt == null || now.isBefore(expiresAt))
}

data class AuthorizationContext(
    val attributes: Map<String, String> = emptyMap()
)

fun interface Policy {
    fun permits(request: AuthorizationRequest): Boolean
}

data class AuthorizationRequest(
    val identityId: String,
    val roles: Set<String>,
    val permissions: Set<String>,
    val scope: ScopeRuleset,
    val entitlement: Entitlement,
    val policy: Policy,
    val context: AuthorizationContext,
    val action: String,
    val resource: Resource,
    val now: Instant
)

enum class DenyReason {
    INVALID_IDENTITY,
    MISSING_ROLE,
    MISSING_PERMISSION,
    SCOPE_DENIED,
    ENTITLEMENT_DENIED,
    POLICY_DENIED,
    CONTEXT_DENIED
}

sealed interface AuthorizationDecision {
    data class Allow(val scopeVersion: Int) : AuthorizationDecision
    data class Deny(val reason: DenyReason) : AuthorizationDecision
}

object AuthorizationEngine {
    fun decide(request: AuthorizationRequest): AuthorizationDecision {
        if (request.identityId.isBlank()) {
            return AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY)
        }

        if (request.roles.isEmpty()) {
            return AuthorizationDecision.Deny(DenyReason.MISSING_ROLE)
        }

        val requiredPermission = "${request.resource.type}:${request.action}"
        if (requiredPermission !in request.permissions) {
            return AuthorizationDecision.Deny(DenyReason.MISSING_PERMISSION)
        }

        if (!request.scope.permits(request.action, request.resource)) {
            return AuthorizationDecision.Deny(DenyReason.SCOPE_DENIED)
        }

        if (!request.entitlement.isActiveAt(request.now)) {
            return AuthorizationDecision.Deny(DenyReason.ENTITLEMENT_DENIED)
        }

        if (request.context.attributes.any { (key, value) -> key.isBlank() || value.isBlank() }) {
            return AuthorizationDecision.Deny(DenyReason.CONTEXT_DENIED)
        }

        if (!request.policy.permits(request)) {
            return AuthorizationDecision.Deny(DenyReason.POLICY_DENIED)
        }

        return AuthorizationDecision.Allow(scopeVersion = request.scope.version)
    }
}
