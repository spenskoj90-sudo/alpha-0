package com.sentinel.core.device

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import java.security.KeyFactory
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.X509EncodedKeySpec

/**
 * Server-side cryptographic verification boundary.
 *
 * The client submits only a challenge ID, public key and signature. The nonce and
 * any expected fingerprint are loaded from trusted server-side challenge state and
 * are therefore not attacker-controlled proof parameters.
 *
 * This verifier proves possession of a P-256 private key. It deliberately does NOT
 * bind a new key to an account or grant authorization. Those remain separate,
 * explicitly authorized server-side decisions.
 */

data class IssuedDeviceChallenge(
    val id: String,
    val nonce: ByteArray,
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
    UNSUPPORTED_KEY,
    INVALID_SIGNATURE,
    DEVICE_MISMATCH,
    CHALLENGE_REPLAYED,
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

class DeviceChallengeVerifier(
    private val challengeStore: ChallengeStore,
    private val auditSink: AuditSink
) {
    fun verify(proof: PresentedDeviceProof): DeviceVerificationResult {
        if (
            proof.challengeId.isBlank() ||
            proof.publicKeyEncoded.isEmpty() ||
            proof.signature.isEmpty()
        ) {
            return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)
        }

        val challenge = challengeStore.find(proof.challengeId)
            ?: return reject("unknown", DeviceVerificationFailure.CHALLENGE_NOT_FOUND)

        if (
            challenge.id != proof.challengeId ||
            challenge.nonce.size < MIN_CHALLENGE_BYTES ||
            challenge.expectedFingerprint?.let(::isValidFingerprint) == false
        ) {
            return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)
        }

        val publicKey = try {
            val key = KeyFactory.getInstance(EC_ALGORITHM)
                .generatePublic(X509EncodedKeySpec(proof.publicKeyEncoded))
            key as? ECPublicKey
                ?: return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        } catch (_: Exception) {
            return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        }

        if (!isP256(publicKey)) {
            return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        }

        val fingerprint = fingerprint(proof.publicKeyEncoded)

        if (
            challenge.expectedFingerprint != null &&
            challenge.expectedFingerprint != fingerprint
        ) {
            return reject(fingerprint, DeviceVerificationFailure.DEVICE_MISMATCH)
        }

        val validSignature = try {
            Signature.getInstance(SIGNATURE_ALGORITHM).apply {
                initVerify(publicKey)
                update(challenge.nonce)
            }.verify(proof.signature)
        } catch (_: Exception) {
            false
        }

        if (!validSignature) {
            return reject(fingerprint, DeviceVerificationFailure.INVALID_SIGNATURE)
        }

        if (!challengeStore.consume(proof.challengeId)) {
            return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_REPLAYED)
        }

        val allowAudit = AuditEvent(
            action = "device.challenge.verify",
            subjectId = fingerprint,
            outcome = "ALLOW",
            reason = null,
            fingerprint = fingerprint
        )

        val auditSucceeded = runCatching { auditSink.record(allowAudit) }.getOrDefault(false)
        if (!auditSucceeded) {
            return DeviceVerificationResult.Rejected(DeviceVerificationFailure.AUDIT_UNAVAILABLE)
        }

        return DeviceVerificationResult.Verified(fingerprint)
    }

    private fun reject(subjectId: String, reason: DeviceVerificationFailure): DeviceVerificationResult.Rejected {
        runCatching {
            auditSink.record(
                AuditEvent(
                    action = "device.challenge.verify",
                    subjectId = subjectId,
                    outcome = "DENY",
                    reason = reason.name,
                    fingerprint = null
                )
            )
        }
        return DeviceVerificationResult.Rejected(reason)
    }

    private fun fingerprint(encodedPublicKey: ByteArray): String =
        MessageDigest.getInstance(HASH_ALGORITHM)
            .digest(encodedPublicKey)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private fun isP256(key: ECPublicKey): Boolean =
        key.params.curve.field.fieldSize == P256_FIELD_SIZE_BITS &&
            key.params.order.bitLength() == P256_ORDER_BITS

    private fun isValidFingerprint(value: String): Boolean =
        value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val EC_ALGORITHM = "EC"
        const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        const val HASH_ALGORITHM = "SHA-256"
        const val MIN_CHALLENGE_BYTES = 32
        const val P256_FIELD_SIZE_BITS = 256
        const val P256_ORDER_BITS = 256
    }
}
