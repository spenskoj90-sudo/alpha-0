package com.sentinel.core.session

import java.sql.Timestamp
import java.sql.SQLException
import java.time.Instant
import javax.sql.DataSource

/** PostgreSQL-backed session store. Tokens are never persisted in raw form. */
class JdbcSessionStore(private val dataSource: DataSource) : SessionRotationStore {
    override fun save(record: SessionRecord): Boolean {
        if (!isValid(record)) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(INSERT_SQL).use { statement ->
                statement.setString(1, record.sessionId)
                statement.setString(2, record.subjectId)
                statement.setBytes(3, record.tokenHash)
                statement.setTimestamp(4, Timestamp.from(record.expiresAt))
                return statement.executeUpdate() == 1
            }
        }
    }

    override fun findByTokenHash(tokenHash: ByteArray): SessionRecord? {
        if (tokenHash.size != TOKEN_HASH_BYTES) return null
        dataSource.connection.use { connection ->
            connection.prepareStatement(SELECT_SQL).use { statement ->
                statement.setBytes(1, tokenHash)
                statement.executeQuery().use { result ->
                    if (!result.next()) return null
                    val sessionId = result.getString("session_id")
                    val subjectId = result.getString("subject_id")
                    val hash = result.getBytes("token_hash")
                    val expiresAt = result.getTimestamp("expires_at")?.toInstant()
                    val revokedAt = result.getTimestamp("revoked_at")?.toInstant()
                    if (sessionId.isNullOrBlank() || sessionId.length > MAX_SESSION_ID_LENGTH ||
                        subjectId.isNullOrBlank() || subjectId.length > MAX_SUBJECT_LENGTH ||
                        hash == null || hash.size != TOKEN_HASH_BYTES || expiresAt == null) {
                        throw SQLException("Invalid persisted session state")
                    }
                    return SessionRecord(sessionId, subjectId, hash, expiresAt, revokedAt)
                }
            }
        }
    }

    override fun revoke(sessionId: String, at: Instant): Boolean {
        if (sessionId.isBlank() || sessionId.length > MAX_SESSION_ID_LENGTH) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(REVOKE_SQL).use { statement ->
                statement.setTimestamp(1, Timestamp.from(at))
                statement.setString(2, sessionId)
                return statement.executeUpdate() == 1
            }
        }
    }

    override fun rotate(oldTokenHash: ByteArray, replacement: SessionRecord, revokedAt: Instant): Boolean {
        if (oldTokenHash.size != TOKEN_HASH_BYTES || !isValid(replacement)) return false
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                connection.prepareStatement(INSERT_ROTATION_SQL).use { insert ->
                    insert.setString(1, replacement.sessionId)
                    insert.setString(2, replacement.subjectId)
                    insert.setBytes(3, replacement.tokenHash)
                    insert.setTimestamp(4, Timestamp.from(replacement.expiresAt))
                    if (insert.executeUpdate() != 1) {
                        connection.rollback()
                        return false
                    }
                }
                connection.prepareStatement(REVOKE_BY_HASH_SQL).use { revoke ->
                    revoke.setTimestamp(1, Timestamp.from(revokedAt))
                    revoke.setBytes(2, oldTokenHash)
                    if (revoke.executeUpdate() != 1) {
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

    private fun isValid(record: SessionRecord): Boolean =
        record.sessionId.isNotBlank() && record.sessionId.length <= MAX_SESSION_ID_LENGTH &&
            record.subjectId.isNotBlank() && record.subjectId.length <= MAX_SUBJECT_LENGTH &&
            record.tokenHash.size == TOKEN_HASH_BYTES && record.expiresAt.isAfter(Instant.now())

    private companion object {
        const val TOKEN_HASH_BYTES = 32
        const val MAX_SESSION_ID_LENGTH = 128
        const val MAX_SUBJECT_LENGTH = 256
        const val INSERT_SQL = """
            INSERT INTO sentinel_sessions(session_id, subject_id, token_hash, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, NULL)
            ON CONFLICT (session_id) DO NOTHING
        """
        const val INSERT_ROTATION_SQL = INSERT_SQL
        const val SELECT_SQL = """
            SELECT session_id, subject_id, token_hash, expires_at, revoked_at
            FROM sentinel_sessions
            WHERE token_hash = ?
        """
        const val REVOKE_SQL = """
            UPDATE sentinel_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE session_id = ? AND revoked_at IS NULL
        """
        const val REVOKE_BY_HASH_SQL = """
            UPDATE sentinel_sessions
            SET revoked_at = COALESCE(revoked_at, ?)
            WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP
        """
    }
}
