package com.sentinel.core.device

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import java.sql.Timestamp
import javax.sql.DataSource

/** Transactional challenge consumption + mandatory audit persistence boundary. */
interface AtomicChallengeAuditStore : ChallengeStore, AuditSink {
    fun consumeAndRecord(challengeId: String, event: AuditEvent): Boolean
}

class JdbcAtomicChallengeAuditStore(private val dataSource: DataSource) : AtomicChallengeAuditStore {
    override fun find(challengeId: String): IssuedDeviceChallenge? = JdbcChallengeStore(dataSource).find(challengeId)
    override fun consume(challengeId: String): Boolean = JdbcChallengeStore(dataSource).consume(challengeId)

    override fun record(event: AuditEvent): Boolean = com.sentinel.core.audit.JdbcAuditSink(dataSource).record(event)

    override fun consumeAndRecord(challengeId: String, event: AuditEvent): Boolean {
        if (challengeId.isBlank() || challengeId.length > 256 || event.subjectId.isBlank()) return false
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                connection.prepareStatement(CONSUME_SQL).use { consume ->
                    consume.setString(1, challengeId)
                    if (consume.executeUpdate() != 1) {
                        connection.rollback()
                        return false
                    }
                }
                connection.prepareStatement(AUDIT_SQL).use { audit ->
                    audit.setTimestamp(1, Timestamp.from(event.timestamp))
                    audit.setString(2, event.action)
                    audit.setString(3, event.subjectId)
                    audit.setString(4, event.outcome)
                    audit.setString(5, event.reason)
                    audit.setString(6, event.fingerprint)
                    if (audit.executeUpdate() != 1) {
                        connection.rollback()
                        return false
                    }
                }
                connection.commit()
                return true
            } catch (_: Exception) {
                runCatching { connection.rollback() }
                return false
            } finally {
                connection.autoCommit = true
            }
        }
    }

    private companion object {
        const val CONSUME_SQL = """
            UPDATE sentinel_device_challenges
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE challenge_id = ?
              AND consumed_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
        """
        const val AUDIT_SQL = """
            INSERT INTO sentinel_audit_events(event_time, action, subject_id, outcome, reason, fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
        """
    }
}
