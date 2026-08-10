package com.sentinel.core.audit

import java.time.Instant

/**
 * Minimal immutable audit event. Persistence is deliberately injected through AuditSink.
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
    fun record(event: AuditEvent)
}
