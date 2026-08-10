package com.sentinel.core.device

import java.sql.Timestamp
import java.security.SecureRandom
import java.time.Instant
import java.util.UUID
import javax.sql.DataSource

class JdbcChallengeIssuer(
    private val dataSource: DataSource,
    private val random: SecureRandom = SecureRandom()
) {
    fun issue(fingerprint: String, expiresAt: Instant): IssuedDeviceChallenge? {
        if (!isValidFingerprint(fingerprint) || !expiresAt.isAfter(Instant.now())) return null
        val nonce = ByteArray(32).also(random::nextBytes)
        val id = UUID.randomUUID().toString()
        return try {
            dataSource.connection.use { connection ->
                connection.prepareStatement(INSERT_SQL).use { statement ->
                    statement.setString(1, id)
                    statement.setBytes(2, nonce)
                    statement.setTimestamp(3, Timestamp.from(expiresAt))
                    statement.setString(4, fingerprint)
                    if (statement.executeUpdate() != 1) return null
                }
            }
            IssuedDeviceChallenge(id, nonce, expiresAt, fingerprint)
        } catch (_: Exception) {
            null
        }
    }

    private fun isValidFingerprint(value: String): Boolean =
        value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val INSERT_SQL = "INSERT INTO sentinel_device_challenges(challenge_id, nonce, expires_at, expected_fingerprint) VALUES (?, ?, ?, ?)"
    }
}
