package com.sentinel.core.device

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import java.security.KeyFactory
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.X509EncodedKeySpec
import java.time.Instant

data class IssuedDeviceChallenge(
    val id: String,
    val nonce: ByteArray,
    val expiresAt: Instant,
    val expectedFingerprint: String? = null
)

data class PresentedDeviceProof(
    val challengeId: String,
    val publicKeyEncoded: ByteArray,
    val signature: ByteArray
)

enum class DeviceVerificationFailure {
    MALFORMED_REQUEST,
    CHALLENGE_NOT_FOUND,
    CHALLENGE_EXPIRED,
    UNSUPPORTED_KEY,
    INVALID_SIGNATURE,
    DEVICE_MISMATCH,
    CHALLENGE_REPLAYED,
    CHALLENGE_STORE_UNAVAILABLE,
    AUDIT_UNAVAILABLE
}

sealed interface DeviceVerificationResult {
    data class Verified(val fingerprint: String) : DeviceVerificationResult
    data class Rejected(val reason: DeviceVerificationFailure) : DeviceVerificationResult
}

interface ChallengeStore {
    fun find(challengeId: String): IssuedDeviceChallenge?
    /** Atomically consumes the challenge. False means it was already consumed. */
    fun consume(challengeId: String): Boolean
}

/** Cryptographic proof-of-possession boundary. Enrollment and authorization are separate controls. */
class DeviceChallengeVerifier(
    private val challengeStore: ChallengeStore,
    private val auditSink: AuditSink,
    private val now: () -> Instant = Instant::now
) {
    fun verify(proof: PresentedDeviceProof): DeviceVerificationResult {
        if (
            proof.challengeId.isBlank() || proof.challengeId.length > MAX_CHALLENGE_ID_LENGTH ||
            proof.publicKeyEncoded.isEmpty() || proof.publicKeyEncoded.size > MAX_PUBLIC_KEY_BYTES ||
            proof.signature.isEmpty() || proof.signature.size > MAX_SIGNATURE_BYTES
        ) return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)

        val challenge = try {
            challengeStore.find(proof.challengeId)
        } catch (_: Exception) {
            return reject("unknown", DeviceVerificationFailure.CHALLENGE_STORE_UNAVAILABLE)
        } ?: return reject("unknown", DeviceVerificationFailure.CHALLENGE_NOT_FOUND)

        if (
            challenge.id != proof.challengeId ||
            challenge.id.isBlank() || challenge.id.length > MAX_CHALLENGE_ID_LENGTH ||
            challenge.nonce.size !in MIN_CHALLENGE_BYTES..MAX_CHALLENGE_BYTES ||
            challenge.expectedFingerprint?.let(::isValidFingerprint) == false
        ) return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)

        if (!now().isBefore(challenge.expiresAt)) {
            return reject("unknown", DeviceVerificationFailure.CHALLENGE_EXPIRED)
        }

        val publicKey = try {
            val key = KeyFactory.getInstance(EC_ALGORITHM)
                .generatePublic(X509EncodedKeySpec(proof.publicKeyEncoded))
            key as? ECPublicKey
                ?: return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        } catch (_: Exception) {
            return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        }

        if (!isP256(publicKey)) return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)

        val fingerprint = fingerprint(proof.publicKeyEncoded)
        if (challenge.expectedFingerprint != null &&
            !MessageDigest.isEqual(
                challenge.expectedFingerprint.toByteArray(Charsets.US_ASCII),
                fingerprint.toByteArray(Charsets.US_ASCII)
            )
        ) return reject(fingerprint, DeviceVerificationFailure.DEVICE_MISMATCH)

        val validSignature = try {
            Signature.getInstance(SIGNATURE_ALGORITHM).apply {
                initVerify(publicKey)
                update(challenge.nonce)
            }.verify(proof.signature)
        } catch (_: Exception) { false }
        if (!validSignature) return reject(fingerprint, DeviceVerificationFailure.INVALID_SIGNATURE)

        // Re-check expiry immediately before the atomic consume to close the
        // verify-at-time-T1 / consume-at-time-T2 expiry window.
        if (!now().isBefore(challenge.expiresAt)) {
            return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_EXPIRED)
        }

        val consumed = try {
            challengeStore.consume(proof.challengeId)
        } catch (_: Exception) {
            return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_STORE_UNAVAILABLE)
        }
        if (!consumed) return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_REPLAYED)

        val allowAudit = AuditEvent(
            action = "device.challenge.verify",
            subjectId = fingerprint,
            outcome = "ALLOW",
            reason = null,
            fingerprint = fingerprint
        )
        if (!runCatching { auditSink.record(allowAudit) }.getOrDefault(false)) {
            return DeviceVerificationResult.Rejected(DeviceVerificationFailure.AUDIT_UNAVAILABLE)
        }
        return DeviceVerificationResult.Verified(fingerprint)
    }

    private fun reject(subjectId: String, reason: DeviceVerificationFailure): DeviceVerificationResult.Rejected {
        runCatching {
            auditSink.record(AuditEvent(
                action = "device.challenge.verify",
                subjectId = subjectId,
                outcome = "DENY",
                reason = reason.name,
                fingerprint = null
            ))
        }
        return DeviceVerificationResult.Rejected(reason)
    }

    private fun fingerprint(encodedPublicKey: ByteArray): String =
        MessageDigest.getInstance(HASH_ALGORITHM).digest(encodedPublicKey)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private fun isP256(key: ECPublicKey): Boolean =
        key.params.curve.field.fieldSize == P256_FIELD_SIZE_BITS && key.params.order.bitLength() == P256_ORDER_BITS

    private fun isValidFingerprint(value: String): Boolean =
        value.length == FINGERPRINT_HEX_LENGTH && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val EC_ALGORITHM = "EC"
        const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        const val HASH_ALGORITHM = "SHA-256"
        const val MIN_CHALLENGE_BYTES = 32
        const val MAX_CHALLENGE_BYTES = 64
        const val MAX_CHALLENGE_ID_LENGTH = 256
        const val MAX_PUBLIC_KEY_BYTES = 512
        const val MAX_SIGNATURE_BYTES = 1024
        const val FINGERPRINT_HEX_LENGTH = 64
        const val P256_FIELD_SIZE_BITS = 256
        const val P256_ORDER_BITS = 256
    }
}
