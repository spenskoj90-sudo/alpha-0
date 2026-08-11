package com.sentinel.core.device

import java.security.AlgorithmParameters
import java.security.KeyFactory
import java.security.MessageDigest
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECParameterSpec
import java.security.spec.X509EncodedKeySpec
import java.time.Instant

/**
 * Explicit enrollment/binding boundary. Registration never grants authorization;
 * it only records a device identity and its security state.
 */
enum class DeviceState { PENDING, ACTIVE, REVOKED }

data class RegisteredDevice(
    val fingerprint: String,
    val publicKeyEncoded: ByteArray,
    val state: DeviceState,
    val registeredAt: Instant,
    val updatedAt: Instant
)

enum class DeviceRegistryFailure {
    MALFORMED_REQUEST,
    ALREADY_REGISTERED,
    NOT_FOUND,
    NOT_ACTIVE,
    REVOKED,
    STORE_UNAVAILABLE
}

sealed interface DeviceRegistryResult {
    data class Registered(val device: RegisteredDevice) : DeviceRegistryResult
    data class Activated(val device: RegisteredDevice) : DeviceRegistryResult
    data class Rejected(val reason: DeviceRegistryFailure) : DeviceRegistryResult
}

interface DeviceRegistryStore {
    fun find(fingerprint: String): RegisteredDevice?
    fun createPending(device: RegisteredDevice): Boolean
    fun updateState(fingerprint: String, state: DeviceState, at: Instant): Boolean
}

class DeviceRegistry(
    private val store: DeviceRegistryStore,
    private val now: () -> Instant = Instant::now
) {
    fun registerPending(fingerprint: String, publicKeyEncoded: ByteArray): DeviceRegistryResult {
        if (!isValidFingerprint(fingerprint) || !isP256PublicKey(publicKeyEncoded)) {
            return DeviceRegistryResult.Rejected(DeviceRegistryFailure.MALFORMED_REQUEST)
        }
        val derivedFingerprint = fingerprintOf(publicKeyEncoded)
        if (!MessageDigest.isEqual(
                fingerprint.toByteArray(Charsets.US_ASCII),
                derivedFingerprint.toByteArray(Charsets.US_ASCII)
            )
        ) return DeviceRegistryResult.Rejected(DeviceRegistryFailure.MALFORMED_REQUEST)

        return try {
            if (store.find(fingerprint) != null) {
                DeviceRegistryResult.Rejected(DeviceRegistryFailure.ALREADY_REGISTERED)
            } else {
                val timestamp = now()
                val device = RegisteredDevice(fingerprint, publicKeyEncoded.copyOf(), DeviceState.PENDING, timestamp, timestamp)
                if (store.createPending(device)) DeviceRegistryResult.Registered(device)
                else DeviceRegistryResult.Rejected(DeviceRegistryFailure.STORE_UNAVAILABLE)
            }
        } catch (_: Exception) {
            DeviceRegistryResult.Rejected(DeviceRegistryFailure.STORE_UNAVAILABLE)
        }
    }

    fun activate(fingerprint: String): DeviceRegistryResult {
        if (!isValidFingerprint(fingerprint)) return DeviceRegistryResult.Rejected(DeviceRegistryFailure.MALFORMED_REQUEST)
        return try {
            val existing = store.find(fingerprint)
                ?: return DeviceRegistryResult.Rejected(DeviceRegistryFailure.NOT_FOUND)
            when (existing.state) {
                DeviceState.REVOKED -> DeviceRegistryResult.Rejected(DeviceRegistryFailure.REVOKED)
                DeviceState.ACTIVE -> DeviceRegistryResult.Activated(existing)
                DeviceState.PENDING -> {
                    val timestamp = now()
                    if (!store.updateState(fingerprint, DeviceState.ACTIVE, timestamp)) {
                        DeviceRegistryResult.Rejected(DeviceRegistryFailure.STORE_UNAVAILABLE)
                    } else {
                        DeviceRegistryResult.Activated(existing.copy(state = DeviceState.ACTIVE, updatedAt = timestamp))
                    }
                }
            }
        } catch (_: Exception) {
            DeviceRegistryResult.Rejected(DeviceRegistryFailure.STORE_UNAVAILABLE)
        }
    }

    fun isActive(fingerprint: String): Boolean = try {
        store.find(fingerprint)?.state == DeviceState.ACTIVE
    } catch (_: Exception) {
        false
    }

    private fun isValidFingerprint(value: String): Boolean =
        value.length == FINGERPRINT_LENGTH && value.all { it in '0'..'9' || it in 'a'..'f' }

    private fun fingerprintOf(encoded: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(encoded)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private fun isP256PublicKey(encoded: ByteArray): Boolean = runCatching {
        if (encoded.isEmpty() || encoded.size > MAX_PUBLIC_KEY_BYTES) return false
        val key = KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(encoded)) as? ECPublicKey ?: return false
        val expected = P256_PARAMS
        key.params.curve == expected.curve &&
            key.params.generator == expected.generator &&
            key.params.order == expected.order &&
            key.params.cofactor == expected.cofactor
    }.getOrDefault(false)

    private companion object {
        const val FINGERPRINT_LENGTH = 64
        const val MAX_PUBLIC_KEY_BYTES = 512
        val P256_PARAMS: ECParameterSpec by lazy {
            AlgorithmParameters.getInstance("EC").apply {
                init(ECGenParameterSpec("secp256r1"))
            }.getParameterSpec(ECParameterSpec::class.java)
        }
    }
}
