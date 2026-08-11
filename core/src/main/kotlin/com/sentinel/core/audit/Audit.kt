package com.sentinel.core.audit

import java.time.Instant

/**
 * Minimal immutable audit event. Persistence is deliberately injected through AuditSink.
 *
 * Returning false is a hard failure: security-sensitive operations must not be
 * reported as successful when the mandatory audit write did not succeed.
 */
data class AuditEvent(
    val action: String,
    val subjectId: String,
    val outcome: String,
    val reason: String?,
    val fingerprint: String?,
    val timestamp: Instant = Instant.now()
)

fun interface AuditSink {
    fun record(event: AuditEvent): Boolean
}
