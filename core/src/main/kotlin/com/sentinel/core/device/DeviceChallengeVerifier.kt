package com.sentinel.core.device

import java.security.KeyFactory
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.X509EncodedKeySpec
import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink

/**
 * Server-side cryptographic verification boundary.
 *
 * This verifier proves possession of the private key corresponding to a submitted
 * P-256 public key. It deliberately does NOT bind the key to an account or grant
 * authorization. Binding and authorization remain separate server-side decisions.
 */

data class DeviceChallenge(
    val id: String,
    val nonce: ByteArray
)

data class DeviceProof(
    val deviceId: String,
    val publicKeyEncoded: ByteArray,
    val signature: ByteArray,
    val challenge: DeviceChallenge
)

enum class DeviceVerificationFailure {
    MALFORMED_REQUEST,
    UNSUPPORTED_KEY,
    INVALID_SIGNATURE,
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
            proof.deviceId.isBlank() ||
            proof.challenge.id.isBlank() ||
            proof.challenge.nonce.size < MIN_CHALLENGE_BYTES ||
            proof.publicKeyEncoded.isEmpty() ||
            proof.signature.isEmpty()
        ) {
            return reject(proof, DeviceVerificationFailure.MALFORMED_REQUEST)
        }

        val publicKey = try {
            val key = KeyFactory.getInstance(EC_ALGORITHM)
                .generatePublic(X509EncodedKeySpec(proof.publicKeyEncoded))
            key as? ECPublicKey
                ?: return reject(proof, DeviceVerificationFailure.UNSUPPORTED_KEY)
        } catch (_: Exception) {
            return reject(proof, DeviceVerificationFailure.UNSUPPORTED_KEY)
        }

        if (!isP256(publicKey)) {
            return reject(proof, DeviceVerificationFailure.UNSUPPORTED_KEY)
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
            return reject(proof, DeviceVerificationFailure.INVALID_SIGNATURE)
        }

        if (!replayGuard.consume(proof.challenge.id)) {
            return reject(proof, DeviceVerificationFailure.CHALLENGE_REPLAYED)
        }

        val fingerprint = MessageDigest.getInstance(HASH_ALGORITHM)
            .digest(proof.publicKeyEncoded)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

        auditSink.record(
            AuditEvent(
                action = "device.challenge.verify",
                subjectId = proof.deviceId,
                outcome = "ALLOW",
                reason = null,
                fingerprint = fingerprint
            )
        )

        return DeviceVerificationResult.Verified(fingerprint)
    }

    private fun reject(
        proof: DeviceProof,
        reason: DeviceVerificationFailure
    ): DeviceVerificationResult.Rejected {
        auditSink.record(
            AuditEvent(
                action = "device.challenge.verify",
                subjectId = proof.deviceId.ifBlank { "unknown" },
                outcome = "DENY",
                reason = reason.name,
                fingerprint = null
            )
        )
        return DeviceVerificationResult.Rejected(reason)
    }

    private fun isP256(key: ECPublicKey): Boolean =
        key.params.curve.field.fieldSize == P256_FIELD_SIZE_BITS &&
            key.params.order.bitLength() == P256_ORDER_BITS

    private companion object {
        const val EC_ALGORITHM = "EC"
        const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        const val HASH_ALGORITHM = "SHA-256"
        const val MIN_CHALLENGE_BYTES = 32
        const val P256_FIELD_SIZE_BITS = 256
        const val P256_ORDER_BITS = 256
    }
}
