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
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", nonce))
        val signature = sign(keyPair, nonce)
        val audit = RecordingAuditSink()
        val verifier = DeviceChallengeVerifier(store, audit)

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, signature)
        )

        assertTrue(result is DeviceVerificationResult.Verified)
        assertEquals(1, audit.events.size)
        assertEquals("ALLOW", audit.events.single().outcome)
        assertTrue(store.consumed)
    }

    @Test
    fun expectedFingerprintBindsChallengeToTheKey() {
        val keyPair = generateP256KeyPair()
        val otherKeyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 9 }
        val expected = fingerprint(otherKeyPair.public.encoded)
        val store = TestChallengeStore(
            IssuedDeviceChallenge("challenge-1", nonce, expectedFingerprint = expected)
        )
        val signature = sign(keyPair, nonce)
        val verifier = DeviceChallengeVerifier(store, RecordingAuditSink())

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, signature)
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.DEVICE_MISMATCH),
            result
        )
        assertTrue(!store.consumed)
    }

    @Test
    fun clientCannotReplaceServerChallengeNonce() {
        val keyPair = generateP256KeyPair()
        val serverNonce = ByteArray(32) { 1 }
        val attackerNonce = ByteArray(32) { 2 }
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", serverNonce))
        val verifier = DeviceChallengeVerifier(store, RecordingAuditSink())

        val result = verifier.verify(
            PresentedDeviceProof(
                "challenge-1",
                keyPair.public.encoded,
                sign(keyPair, attackerNonce)
            )
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.INVALID_SIGNATURE),
            result
        )
        assertTrue(!store.consumed)
    }

    @Test
    fun unknownChallengeIsRejected() {
        val keyPair = generateP256KeyPair()
        val verifier = DeviceChallengeVerifier(TestChallengeStore(null), RecordingAuditSink())

        val result = verifier.verify(
            PresentedDeviceProof("missing", keyPair.public.encoded, byteArrayOf(1, 2, 3))
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.CHALLENGE_NOT_FOUND),
            result
        )
    }

    @Test
    fun invalidSignatureIsRejectedAndChallengeIsNotConsumed() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 7 }
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", nonce))
        val audit = RecordingAuditSink()
        val verifier = DeviceChallengeVerifier(store, audit)

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, byteArrayOf(1, 2, 3))
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.INVALID_SIGNATURE),
            result
        )
        assertTrue(!store.consumed)
        assertEquals("DENY", audit.events.single().outcome)
    }

    @Test
    fun replayIsRejectedAfterValidSignature() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 3 }
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", nonce), consumed = true)
        val verifier = DeviceChallengeVerifier(store, RecordingAuditSink())

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, sign(keyPair, nonce))
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.CHALLENGE_REPLAYED),
            result
        )
    }

    @Test
    fun shortChallengeIsRejected() {
        val keyPair = generateP256KeyPair()
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", ByteArray(16)))
        val audit = RecordingAuditSink()
        val verifier = DeviceChallengeVerifier(store, audit)

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, byteArrayOf(1))
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.MALFORMED_REQUEST),
            result
        )
    }

    @Test
    fun auditFailureFailsClosedAfterChallengeConsumption() {
        val keyPair = generateP256KeyPair()
        val nonce = ByteArray(32) { 4 }
        val store = TestChallengeStore(IssuedDeviceChallenge("challenge-1", nonce))
        val verifier = DeviceChallengeVerifier(
            store,
            auditSink = AuditSink { false }
        )

        val result = verifier.verify(
            PresentedDeviceProof("challenge-1", keyPair.public.encoded, sign(keyPair, nonce))
        )

        assertEquals(
            DeviceVerificationResult.Rejected(DeviceVerificationFailure.AUDIT_UNAVAILABLE),
            result
        )
        assertTrue(store.consumed)
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

    private class TestChallengeStore(
        private val challenge: IssuedDeviceChallenge?,
        var consumed: Boolean = false
    ) : ChallengeStore {
        override fun find(challengeId: String): IssuedDeviceChallenge? =
            challenge?.takeIf { it.id == challengeId }?.takeUnless { consumed }

        override fun consume(challengeId: String): Boolean {
            if (consumed || challenge?.id != challengeId) return false
            consumed = true
            return true
        }
    }

    private class RecordingAuditSink : AuditSink {
        val events = mutableListOf<AuditEvent>()

        override fun record(event: AuditEvent): Boolean {
            events += event
            return true
        }
    }
}
