package com.sentinel.core.device

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import java.security.AlgorithmParameters
import java.security.KeyFactory
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECParameterSpec
import java.security.spec.X509EncodedKeySpec
import java.time.Instant

data class IssuedDeviceChallenge(val id: String, val nonce: ByteArray, val expiresAt: Instant, val expectedFingerprint: String? = null)
data class PresentedDeviceProof(val challengeId: String, val publicKeyEncoded: ByteArray, val signature: ByteArray)

enum class DeviceVerificationFailure { MALFORMED_REQUEST, CHALLENGE_NOT_FOUND, CHALLENGE_EXPIRED, UNSUPPORTED_KEY, INVALID_SIGNATURE, DEVICE_MISMATCH, CHALLENGE_REPLAYED, CHALLENGE_STORE_UNAVAILABLE, AUDIT_UNAVAILABLE }

sealed interface DeviceVerificationResult {
    data class Verified(val fingerprint: String) : DeviceVerificationResult
    data class Rejected(val reason: DeviceVerificationFailure) : DeviceVerificationResult
}

interface ChallengeStore {
    fun find(challengeId: String): IssuedDeviceChallenge?
    fun consume(challengeId: String): Boolean
}

class DeviceChallengeVerifier(
    private val challengeStore: ChallengeStore,
    private val auditSink: AuditSink,
    private val now: () -> Instant = Instant::now,
    private val atomicAuditStore: AtomicChallengeAuditStore? = challengeStore as? AtomicChallengeAuditStore
) {
    fun verify(proof: PresentedDeviceProof): DeviceVerificationResult {
        if (proof.challengeId.isBlank() || proof.challengeId.length > MAX_CHALLENGE_ID_LENGTH || proof.publicKeyEncoded.isEmpty() || proof.publicKeyEncoded.size > MAX_PUBLIC_KEY_BYTES || proof.signature.isEmpty() || proof.signature.size > MAX_SIGNATURE_BYTES) return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)
        val challenge = try { challengeStore.find(proof.challengeId) } catch (_: Exception) { return reject("unknown", DeviceVerificationFailure.CHALLENGE_STORE_UNAVAILABLE) }
            ?: return reject("unknown", DeviceVerificationFailure.CHALLENGE_NOT_FOUND)
        if (challenge.id != proof.challengeId || challenge.id.isBlank() || challenge.id.length > MAX_CHALLENGE_ID_LENGTH || challenge.nonce.size !in MIN_CHALLENGE_BYTES..MAX_CHALLENGE_BYTES || (challenge.expectedFingerprint != null && !isValidFingerprint(challenge.expectedFingerprint))) return reject("unknown", DeviceVerificationFailure.MALFORMED_REQUEST)
        if (!now().isBefore(challenge.expiresAt)) return reject("unknown", DeviceVerificationFailure.CHALLENGE_EXPIRED)
        val publicKey = try {
            KeyFactory.getInstance(EC_ALGORITHM).generatePublic(X509EncodedKeySpec(proof.publicKeyEncoded)) as? ECPublicKey
                ?: return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        } catch (_: Exception) { return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY) }
        if (!isP256(publicKey)) return reject("unknown", DeviceVerificationFailure.UNSUPPORTED_KEY)
        val fingerprint = fingerprint(proof.publicKeyEncoded)
        if (challenge.expectedFingerprint != null && !MessageDigest.isEqual(challenge.expectedFingerprint.toByteArray(Charsets.US_ASCII), fingerprint.toByteArray(Charsets.US_ASCII))) return reject(fingerprint, DeviceVerificationFailure.DEVICE_MISMATCH)
        val validSignature = try { Signature.getInstance(SIGNATURE_ALGORITHM).apply { initVerify(publicKey); update(challenge.nonce) }.verify(proof.signature) } catch (_: Exception) { false }
        if (!validSignature) return reject(fingerprint, DeviceVerificationFailure.INVALID_SIGNATURE)
        if (!now().isBefore(challenge.expiresAt)) return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_EXPIRED)

        val allowAudit = AuditEvent("device.challenge.verify", fingerprint, "ALLOW", null, fingerprint)
        atomicAuditStore?.let { store ->
            val committed = try { store.consumeAndRecord(proof.challengeId, allowAudit) } catch (_: Exception) { false }
            return if (committed) DeviceVerificationResult.Verified(fingerprint) else DeviceVerificationResult.Rejected(DeviceVerificationFailure.CHALLENGE_REPLAYED)
        }
        val consumed = try { challengeStore.consume(proof.challengeId) } catch (_: Exception) { return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_STORE_UNAVAILABLE) }
        if (!consumed) return reject(fingerprint, DeviceVerificationFailure.CHALLENGE_REPLAYED)
        if (!runCatching { auditSink.record(allowAudit) }.getOrDefault(false)) return DeviceVerificationResult.Rejected(DeviceVerificationFailure.AUDIT_UNAVAILABLE)
        return DeviceVerificationResult.Verified(fingerprint)
    }

    private fun reject(subjectId: String, reason: DeviceVerificationFailure): DeviceVerificationResult.Rejected {
        runCatching { auditSink.record(AuditEvent("device.challenge.verify", subjectId, "DENY", reason.name, null)) }
        return DeviceVerificationResult.Rejected(reason)
    }
    private fun fingerprint(encodedPublicKey: ByteArray): String = MessageDigest.getInstance(HASH_ALGORITHM).digest(encodedPublicKey).joinToString("") { "%02x".format(it.toInt() and 0xff) }
    private fun isP256(key: ECPublicKey): Boolean { val actual = key.params; val expected = P256_PARAMS; return actual.curve == expected.curve && actual.generator == expected.generator && actual.order == expected.order && actual.cofactor == expected.cofactor }
    private fun isValidFingerprint(value: String) = value.length == FINGERPRINT_HEX_LENGTH && value.all { it in '0'..'9' || it in 'a'..'f' }

    private companion object {
        const val EC_ALGORITHM = "EC"
        const val SIGNATURE_ALGORITHM = "SHA256withECDSA"
        const val HASH_ALGORITHM = "SHA-256"
        const val MIN_CHALLENGE_BYTES = 32
        const val MAX_CHALLENGE_BYTES = 64
        const val MAX_CHALLENGE_ID_LENGTH = 256
        const val MAX_PUBLIC_KEY_BYTES = 512
        const val MAX_SIGNATURE_BYTES = 128
        const val FINGERPRINT_HEX_LENGTH = 64
        val P256_PARAMS: ECParameterSpec by lazy { AlgorithmParameters.getInstance("EC").apply { init(ECGenParameterSpec("secp256r1")) }.getParameterSpec(ECParameterSpec::class.java) }
    }
}
