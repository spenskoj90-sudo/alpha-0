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
 * The proof contains only cryptographic material and a server-issued challenge.
 * No caller-supplied device/account identifier is trusted as identity. For an
 * already-bound device, the challenge may carry an expected fingerprint; the
 * verifier compares it to the fingerprint derived from the submitted public key.
 *
 * This verifier proves possession of a P-256 private key. It deliberately does NOT
 * bind a new key to an account or grant authorization. Those remain separate,
 * explicitly authorized server-side decisions.
 */

data class DeviceChallenge(
    val id: String,
    val nonce: ByteArray,
    val expectedFingerprint: String? = null
)

data class DeviceProof(
    val publicKeyEncoded: ByteArray,
    val signature: ByteArray,
    val challenge: DeviceChallenge
)

enum class DeviceVerificationFailure {
    MALFORMED_REQUEST,
    UNSUPPORTED_KEY,
    INVALID_SIGNATURE,
    DEVICE_MISMATCH,
    CHALLENGE_REPLAYED
}

sealed interface DeviceVerificationResult {
    data class Verified(val fingerprint: String) : DeviceVerificationResult
    data class Rejected(val reason: DeviceVerificationFailure) : DeviceVerificationResult
}

fun interface ChallengeReplayGuard {
    /** Atomically consumes a challenge. False means it was already consumed or unknown. */
    fun consume(challengeId: String): Boolean
}

class DeviceChallengeVerifier(
    private val replayGuard: ChallengeReplayGuard,
    private val auditSink: AuditSink
) {
    fun verify(proof: DeviceProof): DeviceVerificationResult {
        if (
            proof.challenge.id.isBlank() ||
            proof.challenge.nonce.size < MIN_CHALLENGE_BYTES ||
            proof.publicKeyEncoded.isEmpty() ||
            proof.signature.isEmpty() ||
            proof.challenge.expectedFingerprint?.let(::isValidFingerprint) == false
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
            proof.challenge.expectedFingerprint != null &&
            proof.challenge.expectedFingerprint != fingerprint
        ) {
            return reject(fingerprint, DeviceVerificationFailure.DEVICE_MISMATCH)
        }

        val validSignature = try {
            Signature.getInstance(SIGNATURE_ALGORITHM).apply {
                initVerify(publicKey)
                update(proof.challenge.nonce)
            }.verify(proof.signature)
        } catch (_: Exception) {
            false
        }

        if (!validSignature) {
            return reject(fingerprint, DeviceVerificationFailure.INVALID_SIGNATURE)
        }

        if (!replayGuard.consume(proof.challenge.id)) {
            return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_REPLAYED)
        }

        auditSink.record(
            AuditEvent(
                action = "device.challenge.verify",
                subjectId = fingerprint,
                outcome = "ALLOW",
                reason = null,
                fingerprint = fingerprint
            )
        )

        return DeviceVerificationResult.Verified(fingerprint)
    }

    private fun reject(subjectId: String, reason: DeviceVerificationFailure): DeviceVerificationResult.Rejected {
        auditSink.record(
            AuditEvent(
                action = "device.challenge.verify",
                subjectId = subjectId,
                outcome = "DENY",
                reason = reason.name,
                fingerprint = null
            )
        )
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
