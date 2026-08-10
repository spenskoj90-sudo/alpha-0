package com.sentinel.core.device

import java.sql.Timestamp
import java.time.Instant
import javax.sql.DataSource

class JdbcDeviceRegistryStore(private val dataSource: DataSource) : DeviceRecoveryStore {
    override fun find(fingerprint: String): RegisteredDevice? {
        if (!isValidFingerprint(fingerprint)) return null
        dataSource.connection.use { connection ->
            connection.prepareStatement(SELECT_SQL).use { statement ->
                statement.setString(1, fingerprint)
                statement.executeQuery().use { result ->
                    if (!result.next()) return null
                    return RegisteredDevice(
                        fingerprint = result.getString("fingerprint"),
                        publicKeyEncoded = result.getBytes("public_key"),
                        state = DeviceState.valueOf(result.getString("state")),
                        registeredAt = result.getTimestamp("registered_at").toInstant(),
                        updatedAt = result.getTimestamp("updated_at").toInstant()
                    )
                }
            }
        }
    }

    override fun createPending(device: RegisteredDevice): Boolean {
        if (!isValidFingerprint(device.fingerprint) || device.publicKeyEncoded.size > 512) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(INSERT_SQL).use { statement ->
                statement.setString(1, device.fingerprint)
                statement.setBytes(2, device.publicKeyEncoded)
                statement.setString(3, device.state.name)
                statement.setTimestamp(4, Timestamp.from(device.registeredAt))
                statement.setTimestamp(5, Timestamp.from(device.updatedAt))
                return statement.executeUpdate() == 1
            }
        }
    }

    override fun updateState(fingerprint: String, state: DeviceState, at: Instant): Boolean {
        if (!isValidFingerprint(fingerprint)) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(UPDATE_SQL).use { statement ->
                statement.setString(1, state.name)
                statement.setTimestamp(2, Timestamp.from(at))
                statement.setString(3, fingerprint)
                return statement.executeUpdate() == 1
            }
        }
    }

    override fun saveRecoveryCode(deviceFingerprint: String, codeHash: ByteArray, expiresAt: Instant): Boolean {
        if (!isValidFingerprint(deviceFingerprint) || codeHash.size != 32 || !expiresAt.isAfter(Instant.now())) return false
        dataSource.connection.use { connection ->
            connection.prepareStatement(INSERT_RECOVERY_SQL).use { statement ->
                statement.setString(1, deviceFingerprint)
                statement.setBytes(2, codeHash)
                statement.setTimestamp(3, Timestamp.from(expiresAt))
                return statement.executeUpdate() == 1
            }
        }
    }

    override fun recover(deviceFingerprint: String, codeHash: ByteArray, newFingerprint: String, newPublicKey: ByteArray, at: Instant): Boolean {
        if (!isValidFingerprint(deviceFingerprint) || !isValidFingerprint(newFingerprint) || codeHash.size != 32 || newPublicKey.isEmpty() || newPublicKey.size > 512) return false
        dataSource.connection.use { connection ->
            connection.autoCommit = false
            try {
                connection.prepareStatement(CONSUME_RECOVERY_SQL).use { consume ->
                    consume.setTimestamp(1, Timestamp.from(at))
                    consume.setString(2, deviceFingerprint)
                    consume.setBytes(3, codeHash)
                    if (consume.executeUpdate() != 1) {
                        connection.rollback()
                        return false
                    }
                }
                connection.prepareStatement(ROTATE_KEY_SQL).use { rotate ->
                    rotate.setString(1, newFingerprint)
                    rotate.setBytes(2, newPublicKey)
                    rotate.setTimestamp(3, Timestamp.from(at))
                    rotate.setString(4, deviceFingerprint)
                    if (rotate.executeUpdate() != 1) {
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

    private fun isValidFingerprint(value: String): Boolean =
        value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val SELECT_SQL = "SELECT fingerprint, public_key, state, registered_at, updated_at FROM sentinel_devices WHERE fingerprint = ?"
        const val INSERT_SQL = "INSERT INTO sentinel_devices(fingerprint, public_key, state, registered_at, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT (fingerprint) DO NOTHING"
        const val UPDATE_SQL = "UPDATE sentinel_devices SET state = ?, updated_at = ? WHERE fingerprint = ?"
        const val INSERT_RECOVERY_SQL = "INSERT INTO sentinel_device_recovery_codes(device_fingerprint, code_hash, expires_at) VALUES (?, ?, ?)"
        const val CONSUME_RECOVERY_SQL = "UPDATE sentinel_device_recovery_codes SET consumed_at = ? WHERE device_fingerprint = ? AND code_hash = ? AND consumed_at IS NULL AND expires_at > CURRENT_TIMESTAMP"
        const val ROTATE_KEY_SQL = "UPDATE sentinel_devices SET fingerprint = ?, public_key = ?, updated_at = ? WHERE fingerprint = ? AND state = 'ACTIVE'"
    }
}
