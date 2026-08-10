package com.sentinel.core.device

import java.sql.ResultSet
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

    private fun ResultSet.toChallenge(): IssuedDeviceChallenge = IssuedDeviceChallenge(
        id = getString("challenge_id"),
        nonce = getBytes("nonce"),
        expiresAt = getTimestamp("expires_at").toInstant(),
        expectedFingerprint = getString("expected_fingerprint")
    )

    private companion object {
        const val MAX_ID_LENGTH = 256
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
