package com.sentinel.core.authorization

import java.time.Instant

private const val MAX_TEXT_LENGTH = 256
private const val MAX_PERMISSION_LENGTH = 513
private const val MAX_SET_SIZE = 128
private const val MAX_SCOPE_RULES = 512
private const val MAX_CONTEXT_ATTRIBUTES = 64

/**
 * Deterministic authorization domain for Sentinel Core.
 *
 * Security invariant: malformed input and evaluation failures fail closed.
 * Resource limits are enforced at this boundary to reduce memory/CPU abuse.
 */

data class Resource(val type: String, val id: String)

data class ScopeRule(
    val resourceType: String,
    val resourceId: String? = null,
    val actions: Set<String>
) {
    fun permits(action: String, resource: Resource): Boolean =
        action in actions && resourceType == resource.type &&
            (resourceId == null || resourceId == resource.id)

    fun isValid(): Boolean =
        resourceType.isNotBlank() && resourceType.length <= MAX_TEXT_LENGTH &&
            (resourceId == null || (resourceId.isNotBlank() && resourceId.length <= MAX_TEXT_LENGTH)) &&
            actions.isNotEmpty() && actions.size <= MAX_SET_SIZE &&
            actions.all { it.isNotBlank() && it.length <= MAX_TEXT_LENGTH }
}

data class ScopeRuleset(val version: Int, val rules: List<ScopeRule>) {
    fun permits(action: String, resource: Resource): Boolean = rules.any { it.permits(action, resource) }
    fun isValid(): Boolean = version > 0 && rules.isNotEmpty() &&
        rules.size <= MAX_SCOPE_RULES && rules.all(ScopeRule::isValid)
}

enum class EntitlementStatus { ACTIVE, EXPIRED, REVOKED, SUSPENDED }

data class Entitlement(
    val source: String,
    val status: EntitlementStatus,
    val startsAt: Instant,
    val expiresAt: Instant?
) {
    fun isActiveAt(now: Instant): Boolean =
        source.isNotBlank() && status == EntitlementStatus.ACTIVE &&
            !now.isBefore(startsAt) && (expiresAt == null || now.isBefore(expiresAt))

    fun isValid(): Boolean = source.isNotBlank() && source.length <= MAX_TEXT_LENGTH &&
        (expiresAt == null || !expiresAt.isBefore(startsAt))
}

data class AuthorizationContext(val attributes: Map<String, String> = emptyMap()) {
    fun isValid(): Boolean = attributes.size <= MAX_CONTEXT_ATTRIBUTES && attributes.all { (key, value) ->
        key.isNotBlank() && key.length <= MAX_TEXT_LENGTH &&
            value.isNotBlank() && value.length <= MAX_TEXT_LENGTH
    }
}

fun interface Policy { fun permits(request: AuthorizationRequest): Boolean }

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
    MALFORMED_REQUEST, INVALID_IDENTITY, MISSING_ROLE, MISSING_PERMISSION,
    SCOPE_DENIED, ENTITLEMENT_DENIED, POLICY_DENIED, CONTEXT_DENIED
}

sealed interface AuthorizationDecision {
    data class Allow(val scopeVersion: Int) : AuthorizationDecision
    data class Deny(val reason: DenyReason) : AuthorizationDecision
}

object AuthorizationEngine {
    fun decide(request: AuthorizationRequest): AuthorizationDecision {
        if (!isRequestWellFormed(request)) return deny(DenyReason.MALFORMED_REQUEST)
        if (request.identityId.isBlank() || request.identityId.length > MAX_TEXT_LENGTH) {
            return deny(DenyReason.INVALID_IDENTITY)
        }
        if (request.requiredRole !in request.roles) return deny(DenyReason.MISSING_ROLE)

        val requiredPermission = "${request.resource.type}:${request.action}"
        if (requiredPermission !in request.permissions) return deny(DenyReason.MISSING_PERMISSION)
        if (!request.scope.permits(request.action, request.resource)) return deny(DenyReason.SCOPE_DENIED)
        if (!request.entitlement.isActiveAt(request.now)) return deny(DenyReason.ENTITLEMENT_DENIED)
        if (!request.context.isValid()) return deny(DenyReason.CONTEXT_DENIED)

        val policyPermits = try { request.policy.permits(request) } catch (_: Exception) { false }
        if (!policyPermits) return deny(DenyReason.POLICY_DENIED)
        return AuthorizationDecision.Allow(request.scope.version)
    }

    private fun deny(reason: DenyReason) = AuthorizationDecision.Deny(reason)

    private fun isRequestWellFormed(request: AuthorizationRequest): Boolean =
        request.roles.isNotEmpty() && request.roles.size <= MAX_SET_SIZE &&
            request.roles.all { it.isNotBlank() && it.length <= MAX_TEXT_LENGTH } &&
            request.permissions.isNotEmpty() && request.permissions.size <= MAX_SET_SIZE &&
            request.permissions.all { it.isNotBlank() && it.length <= MAX_PERMISSION_LENGTH } &&
            request.requiredRole.isNotBlank() && request.requiredRole.length <= MAX_TEXT_LENGTH &&
            request.action.isNotBlank() && request.action.length <= MAX_TEXT_LENGTH &&
            request.resource.type.isNotBlank() && request.resource.type.length <= MAX_TEXT_LENGTH &&
            request.resource.id.isNotBlank() && request.resource.id.length <= MAX_TEXT_LENGTH &&
            request.scope.isValid() && request.entitlement.isValid()
}
