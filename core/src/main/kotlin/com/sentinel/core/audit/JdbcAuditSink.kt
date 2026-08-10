package com.sentinel.core.audit

import java.sql.Timestamp
import javax.sql.DataSource

/** Minimal PostgreSQL audit sink. Audit writes are explicit and fail closed. */
class JdbcAuditSink(private val dataSource: DataSource) : AuditSink {
    override fun record(event: AuditEvent): Boolean {
        if (!isValid(event)) return false
        return try {
            dataSource.connection.use { connection ->
                connection.prepareStatement(INSERT_SQL).use { statement ->
                    statement.setTimestamp(1, Timestamp.from(event.timestamp))
                    statement.setString(2, event.action)
                    statement.setString(3, event.subjectId)
                    statement.setString(4, event.outcome)
                    statement.setString(5, event.reason)
                    statement.setString(6, event.fingerprint)
                    statement.executeUpdate() == 1
                }
            }
        } catch (_: Exception) {
            false
        }
    }

    private fun isValid(event: AuditEvent): Boolean =
        event.action.isNotBlank() && event.action.length <= 128 &&
            event.subjectId.isNotBlank() && event.subjectId.length <= 256 &&
            event.outcome in setOf("ALLOW", "DENY") &&
            event.reason?.length?.let { it <= 256 } != false &&
            event.fingerprint?.matches(Regex("[0-9a-f]{64}")) != false

    private companion object {
        const val INSERT_SQL = """
            INSERT INTO sentinel_audit_events(event_time, action, subject_id, outcome, reason, fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
        """
    }
}
