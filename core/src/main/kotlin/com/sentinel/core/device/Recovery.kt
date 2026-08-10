package com.sentinel.core.device

import java.security.MessageDigest
import java.security.SecureRandom
import java.time.Duration
import java.time.Instant
import java.util.Base64

/** Persistence boundary for recovery. Recover must consume the one-time code and rotate the key atomically. */
interface DeviceRecoveryStore : DeviceRegistryStore {
    fun saveRecoveryCode(deviceFingerprint: String, codeHash: ByteArray, expiresAt: Instant): Boolean
    fun recover(deviceFingerprint: String, codeHash: ByteArray, newFingerprint: String, newPublicKey: ByteArray, at: Instant): Boolean
}

sealed interface RecoveryResult {
    data class Issued(val code: String, val expiresAt: Instant) : RecoveryResult
    data object Recovered : RecoveryResult
    data class Rejected(val reason: String) : RecoveryResult
}

class DeviceRecoveryService(
    private val store: DeviceRecoveryStore,
    private val random: SecureRandom = SecureRandom(),
    private val now: () -> Instant = Instant::now
) {
    fun issueCode(fingerprint: String, lifetime: Duration = Duration.ofMinutes(15)): RecoveryResult {
        if (!validFingerprint(fingerprint) || lifetime.isNegative || lifetime.isZero || lifetime > MAX_LIFETIME) {
            return RecoveryResult.Rejected("malformed_request")
        }
        val raw = ByteArray(CODE_BYTES).also(random::nextBytes)
        val code = Base64.getUrlEncoder().withoutPadding().encodeToString(raw)
        val expiresAt = now().plus(lifetime)
        return try {
            if (store.saveRecoveryCode(fingerprint, sha256(raw), expiresAt)) RecoveryResult.Issued(code, expiresAt)
            else RecoveryResult.Rejected("store_unavailable")
        } catch (_: Exception) {
            RecoveryResult.Rejected("store_unavailable")
        }
    }

    fun rotateKey(oldFingerprint: String, newPublicKey: ByteArray, recoveryCode: String): RecoveryResult {
        if (!validFingerprint(oldFingerprint) || newPublicKey.isEmpty() || newPublicKey.size > MAX_PUBLIC_KEY_BYTES || recoveryCode.isBlank()) {
            return RecoveryResult.Rejected("malformed_request")
        }
        val rawCode = try { Base64.getUrlDecoder().decode(recoveryCode) } catch (_: IllegalArgumentException) {
            return RecoveryResult.Rejected("malformed_request")
        }
        if (rawCode.size != CODE_BYTES) return RecoveryResult.Rejected("malformed_request")
        val newFingerprint = sha256(newPublicKey).toHex()
        return try {
            if (store.find(oldFingerprint)?.state != DeviceState.ACTIVE) return RecoveryResult.Rejected("device_not_active")
            if (store.recover(oldFingerprint, sha256(rawCode), newFingerprint, newPublicKey.copyOf(), now())) {
                RecoveryResult.Recovered
            } else RecoveryResult.Rejected("invalid_or_expired_code")
        } catch (_: Exception) {
            RecoveryResult.Rejected("store_unavailable")
        }
    }

    private fun validFingerprint(value: String) = value.length == FINGERPRINT_LENGTH && value.all { it in '0'..'9' || it in 'a'..'f' }
    private fun sha256(value: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(value)
    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private companion object {
        const val CODE_BYTES = 32
        const val MAX_PUBLIC_KEY_BYTES = 512
        const val FINGERPRINT_LENGTH = 64
        val MAX_LIFETIME: Duration = Duration.ofHours(24)
    }
}
