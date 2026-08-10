package com.sentinel.core.authorization

import java.time.Instant

/**
 * Deterministic authorization domain for Sentinel Core.
 *
 * This module intentionally contains no transport, persistence, billing, or UI code.
 * The server/API adapter must invoke this engine before protected operations are executed.
 *
 * Security invariant: malformed input and evaluation failures fail closed.
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

    fun isValid(): Boolean =
        resourceType.isNotBlank() &&
            (resourceId == null || resourceId.isNotBlank()) &&
            actions.isNotEmpty() &&
            actions.none { it.isBlank() }
}

data class ScopeRuleset(
    val version: Int,
    val rules: List<ScopeRule>
) {
    fun permits(action: String, resource: Resource): Boolean =
        rules.any { it.permits(action, resource) }

    fun isValid(): Boolean =
        version > 0 && rules.isNotEmpty() && rules.all(ScopeRule::isValid)
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
        source.isNotBlank() &&
            status == EntitlementStatus.ACTIVE &&
            !now.isBefore(startsAt) &&
            (expiresAt == null || now.isBefore(expiresAt))

    fun isValid(): Boolean =
        source.isNotBlank() &&
            (expiresAt == null || !expiresAt.isBefore(startsAt))
}

data class AuthorizationContext(
    val attributes: Map<String, String> = emptyMap()
) {
    fun isValid(): Boolean =
        attributes.keys.none { it.isBlank() } &&
            attributes.values.none { it.isBlank() }
}

fun interface Policy {
    fun permits(request: AuthorizationRequest): Boolean
}

data class AuthorizationRequest(
    val identityId: String,
    val roles: Set<String>,
    val requiredRole: String,
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
    MALFORMED_REQUEST,
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
        if (!isRequestWellFormed(request)) {
            return AuthorizationDecision.Deny(DenyReason.MALFORMED_REQUEST)
        }

        if (request.identityId.isBlank()) {
            return AuthorizationDecision.Deny(DenyReason.INVALID_IDENTITY)
        }

        if (request.requiredRole.isBlank() || request.roles.isEmpty() || request.requiredRole !in request.roles) {
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

        if (!request.context.isValid()) {
            return AuthorizationDecision.Deny(DenyReason.CONTEXT_DENIED)
        }

        val policyPermits = try {
            request.policy.permits(request)
        } catch (_: Exception) {
            false
        }

        if (!policyPermits) {
            return AuthorizationDecision.Deny(DenyReason.POLICY_DENIED)
        }

        return AuthorizationDecision.Allow(scopeVersion = request.scope.version)
    }

    private fun isRequestWellFormed(request: AuthorizationRequest): Boolean =
        request.roles.none { it.isBlank() } &&
            request.permissions.none { it.isBlank() } &&
            request.action.isNotBlank() &&
            request.resource.type.isNotBlank() &&
            request.resource.id.isNotBlank() &&
            request.scope.isValid() &&
            request.entitlement.isValid()
}
