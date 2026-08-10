package com.sentinel.core.device

import com.sentinel.core.audit.AuditEvent
import com.sentinel.core.audit.AuditSink
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature

class DeviceChallengeVerifierTest {

    @Test
    fun validProofIsAcceptedAndAudited() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { it.toByte() }
        val challenge = DeviceChallenge("challenge-1", nonce)
        val signature = sign(keyPair, nonce)
        val audit = RecordingAuditSink()
        val consumed = mutableSetOf<String>()
        val verifier = DeviceChallengeVerifier(
            replayGuard = ChallengeReplayGuard { consumed.add(it) },
            auditSink = audit
        )

        val result = verifier.verify(
            DeviceProof(keyPair.public.encoded, signature, challenge)
        )

        assertTrue(result is DeviceVerificationResult.Verified)
        assertEquals(1, audit.events.size)
        assertEquals("ALLOW", audit.events.single().outcome)
    }

    @Test
    fun expectedFingerprintBindsChallengeToTheKey() {
        val keyPair = generateP256KeyPair()
        val otherKeyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 9 }
        val expected = fingerprint(otherKeyPair.public.encoded)
        val challenge = DeviceChallenge("challenge-1", nonce, expectedFingerprint = expected)
        val signature = sign(keyPair, nonce)
        val verifier = DeviceChallengeVerifier(
            replayGuard = ChallengeReplayGuard { true },
            auditSink = RecordingAuditSink()
        )

        val result = verifier.verify(DeviceProof(keyPair.public.encoded, signature, challenge))

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.DEVICE_MISMATCH),
            result
        )
    }

    @Test
    fun invalidSignatureIsRejectedAndChallengeIsNotConsumed() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 7 }
        val audit = RecordingAuditSink()
        val consumed = mutableSetOf<String>()
        val verifier = DeviceChallengeVerifier(
            replayGuard = ChallengeReplayGuard { consumed.add(it) },
            auditSink = audit
        )

        val result = verifier.verify(
            DeviceProof(
                keyPair.public.encoded,
                byteArrayOf(1, 2, 3),
                DeviceChallenge("challenge-1", nonce)
            )
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.INVALID_SIGNATURE),
            result
        )
        assertTrue(consumed.isEmpty())
        assertEquals("DENY", audit.events.single().outcome)
    }

    @Test
    fun replayIsRejectedAfterValidSignature() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 3 }
        val signature = sign(keyPair, nonce)
        val challenge = DeviceChallenge("challenge-1", nonce)
        val audit = RecordingAuditSink()
        val verifier = DeviceChallengeVerifier(
            replayGuard = ChallengeReplayGuard { false },
            auditSink = audit
        )

        val result = verifier.verify(
            DeviceProof(keyPair.public.encoded, signature, challenge)
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.CHALLENGE_REPLAYED),
            result
        )
        assertEquals("DENY", audit.events.single().outcome)
    }

    @Test
    fun shortChallengeIsRejected() {
        val keyPair = generateP256KeyPair()
        val audit = RecordingAuditSink()
        val verifier = DeviceChallengeVerifier(
            replayGuard = ChallengeReplayGuard { true },
            auditSink = audit
        )

        val result = verifier.verify(
            DeviceProof(
                keyPair.public.encoded,
                byteArrayOf(1),
                DeviceChallenge("challenge-1", ByteArray(16))
            )
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.MALFORMED_REQUEST),
            result
        )
    }

    private fun generateP256KeyPair(): KeyPair =
        KeyPairGenerator.getInstance("EC").apply {
            initialize(256)
        }.generateKeyPair()

    private fun sign(keyPair: KeyPair, nonce: ByteArray): ByteArray =
        Signature.getInstance("SHA256withECDSA").apply {
            initSign(keyPair.private)
            update(nonce)
        }.sign()

    private fun fingerprint(encodedPublicKey: ByteArray): String =
        MessageDigest.getInstance("SHA-256")
            .digest(encodedPublicKey)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    private class RecordingAuditSink : AuditSink {
        val events = mutableListOf<AuditEvent>()

        override fun record(event: AuditEvent) {
            events += event
        }
    }
}
