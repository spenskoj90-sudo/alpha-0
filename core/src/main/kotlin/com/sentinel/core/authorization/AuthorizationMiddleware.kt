package com.sentinel.core.authorization

import com.sentinel.core.session.SessionManager
import com.sentinel.core.session.SessionResult
import java.time.Instant

/** Trusted server-side authorization profile. No client-provided roles or permissions are accepted. */
data class AuthorizationProfile(
    val roles: Set<String>,
    val requiredRole: String,
    val permissions: Set<String>,
    val scope: ScopeRuleset,
    val entitlement: Entitlement,
    val policy: Policy,
    val context: AuthorizationContext = AuthorizationContext()
)

fun interface AuthorizationProfileStore {
    fun find(subjectId: String): AuthorizationProfile?
}

sealed interface ProtectedAuthorizationResult {
    data class Allow(val sessionId: String, val subjectId: String, val scopeVersion: Int) : ProtectedAuthorizationResult
    data class Deny(val status: Int, val reason: String) : ProtectedAuthorizationResult
}

class AuthorizationMiddleware(
    private val sessions: SessionManager,
    private val profiles: AuthorizationProfileStore,
    private val now: () -> Instant = Instant::now
) {
    fun authorize(bearerToken: String, action: String, resource: Resource): ProtectedAuthorizationResult {
        val authentication = sessions.authenticate(bearerToken)
        if (authentication !is SessionResult.Authenticated) {
            return ProtectedAuthorizationResult.Deny(401, "unauthorized")
        }
        val profile = try { profiles.find(authentication.subjectId) } catch (_: Exception) { null }
            ?: return ProtectedAuthorizationResult.Deny(403, "forbidden")
        val request = AuthorizationRequest(
            identityId = authentication.subjectId,
            roles = profile.roles,
            requiredRole = profile.requiredRole,
            permissions = profile.permissions,
            scope = profile.scope,
            entitlement = profile.entitlement,
            policy = profile.policy,
            context = profile.context,
            action = action,
            resource = resource,
            now = now()
        )
        return when (val decision = AuthorizationEngine.decide(request)) {
            is AuthorizationDecision.Allow -> ProtectedAuthorizationResult.Allow(authentication.sessionId, authentication.subjectId, decision.scopeVersion)
            is AuthorizationDecision.Deny -> ProtectedAuthorizationResult.Deny(403, decision.reason.name.lowercase())
        }
    }
}
