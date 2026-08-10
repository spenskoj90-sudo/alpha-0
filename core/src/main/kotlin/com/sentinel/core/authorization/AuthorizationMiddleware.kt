package com.sentinel.core.authorization

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
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
    private val now: () -> Instant = Instant::now,
    private val auditSink: AuditSink? = null
) {
    fun authorize(bearerToken: String, action: String, resource: Resource): ProtectedAuthorizationResult {
        val authentication = sessions.authenticate(bearerToken)
        if (authentication !is SessionResult.Authenticated) {
            return auditOrDeny(
                AuditEvent("authorization", "unknown", "DENY", "unauthorized", null, now()),
                ProtectedAuthorizationResult.Deny(401, "unauthorized")
            )
        }
        val profile = try { profiles.find(authentication.subjectId) } catch (_: Exception) { null }
            ?: return auditOrDeny(
                AuditEvent("authorization", authentication.subjectId, "DENY", "profile_unavailable", null, now()),
                ProtectedAuthorizationResult.Deny(403, "forbidden")
            )
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
            is AuthorizationDecision.Allow -> auditOrDeny(
                AuditEvent("authorization", authentication.subjectId, "ALLOW", null, null, now()),
                ProtectedAuthorizationResult.Allow(authentication.sessionId, authentication.subjectId, decision.scopeVersion)
            )
            is AuthorizationDecision.Deny -> auditOrDeny(
                AuditEvent(
                    "authorization:${action.take(96)}",
                    authentication.subjectId,
                    "DENY",
                    "${decision.reason.name.lowercase()};resource=${resource.type}:${resource.id}".take(256),
                    null,
                    now()
                ),
                ProtectedAuthorizationResult.Deny(403, decision.reason.name.lowercase())
            )
        }
    }

    private fun auditOrDeny(event: AuditEvent, result: ProtectedAuthorizationResult): ProtectedAuthorizationResult {
        if (auditSink == null) return result
        return try {
            if (auditSink.record(event)) result
            else ProtectedAuthorizationResult.Deny(503, "audit_unavailable")
        } catch (_: Exception) {
            ProtectedAuthorizationResult.Deny(503, "audit_unavailable")
        }
    }
}
