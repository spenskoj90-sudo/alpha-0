package com.sentinel.core.device

import java.sql.Timestamp
import javax.sql.DataSource

class JdbcDeviceRegistryStore(private val dataSource: DataSource) : DeviceRegistryStore {
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

    override fun updateState(fingerprint: String, state: DeviceState, at: java.time.Instant): Boolean {
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

    private fun isValidFingerprint(value: String): Boolean =
        value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val SELECT_SQL = "SELECT fingerprint, public_key, state, registered_at, updated_at FROM sentinel_devices WHERE fingerprint = ?"
        const val INSERT_SQL = "INSERT INTO sentinel_devices(fingerprint, public_key, state, registered_at, updated_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT (fingerprint) DO NOTHING"
        const val UPDATE_SQL = "UPDATE sentinel_devices SET state = ?, updated_at = ? WHERE fingerprint = ?"
    }
}
