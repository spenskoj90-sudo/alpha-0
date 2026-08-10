package com.sentinel.core.device

import java.sql.ResultSet
import java.sql.SQLException
import javax.sql.DataSource

/**
 * PostgreSQL-backed challenge store.
 *
 * Replay prevention is enforced by one atomic UPDATE. The database remains the
 * source of truth for consumed state and expiry.
 */
class JdbcChallengeStore(
    private val dataSource: DataSource
) : ChallengeStore {

    override fun find(challengeId: String): IssuedDeviceChallenge? {
        if (challengeId.isBlank() || challengeId.length > MAX_ID_LENGTH) return null
        dataSource.connection.use { connection ->
            connection.prepareStatement(SELECT_SQL).use { statement ->
                statement.setString(1, challengeId)
                statement.executeQuery().use { result ->
                    return if (result.next()) result.toChallenge() else null
                }
            }
        }
    }

    override fun consume(challengeId: String): Boolean {
        if (challengeId.isBlank() || challengeId.length > MAX_ID_LENGTH) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(CONSUME_SQL).use { statement ->
                statement.setString(1, challengeId)
                return statement.executeUpdate() == 1
            }
        }
    }

    private fun ResultSet.toChallenge(): IssuedDeviceChallenge {
        val id = getString("challenge_id")
        val nonce = getBytes("nonce")
        val expiresAt = getTimestamp("expires_at")?.toInstant()
        val fingerprint = getString("expected_fingerprint")

        if (id.isNullOrBlank() || id.length > MAX_ID_LENGTH ||
            nonce == null || nonce.size !in MIN_NONCE_BYTES..MAX_NONCE_BYTES ||
            expiresAt == null || fingerprint?.let(::isValidFingerprint) == false
        ) {
            throw SQLException("Invalid persisted challenge state")
        }

        return IssuedDeviceChallenge(
            id = id,
            nonce = nonce,
            expiresAt = expiresAt,
            expectedFingerprint = fingerprint
        )
    }

    private fun isValidFingerprint(value: String): Boolean =
        value.length == FINGERPRINT_LENGTH &&
            value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val MAX_ID_LENGTH = 256
        const val MIN_NONCE_BYTES = 32
        const val MAX_NONCE_BYTES = 64
        const val FINGERPRINT_LENGTH = 64
        const val SELECT_SQL = """
            SELECT challenge_id, nonce, expires_at, expected_fingerprint
            FROM sentinel_device_challenges
            WHERE challenge_id = ?
        """
        const val CONSUME_SQL = """
            UPDATE sentinel_device_challenges
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE challenge_id = ?
              AND consumed_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
        """
    }
}
