package com.sentinel.core.device

import com.sentinel.core.audit.AuditSink
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.security.KeyPairGenerator
import java.security.Signature
import java.time.Instant

class BoundDeviceChallengeVerifierTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")

    @Test
    fun revokedDeviceIsDeniedBeforeCryptographicVerification() {
        val keys = KeyPairGenerator.getInstance("EC").apply { initialize(256) }.generateKeyPair()
        val fingerprint = java.security.MessageDigest.getInstance("SHA-256").digest(keys.public.encoded)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val registryStore = Store(
            RegisteredDevice(fingerprint, keys.public.encoded, DeviceState.REVOKED, now, now)
        )
        val registry = DeviceRegistry(registryStore) { now }
        val challengeStore = ChallengeStoreImpl(IssuedDeviceChallenge("c1", ByteArray(32), now.plusSeconds(60), fingerprint))
        val verifier = DeviceChallengeVerifier(challengeStore, AuditSink { true }) { now }
        val result = BoundDeviceChallengeVerifier(registry, verifier).verify(
            PresentedDeviceProof("c1", keys.public.encoded, sign(keys, ByteArray(32)))
        )
        assertEquals(DeviceVerificationResult.Rejected(DeviceVerificationFailure.DEVICE_MISMATCH), result)
        assertTrue(!challengeStore.consumed)
    }

    private fun sign(keys: java.security.KeyPair, nonce: ByteArray): ByteArray =
        Signature.getInstance("SHA256withECDSA").apply {
            initSign(keys.private)
            update(nonce)
        }.sign()

    private class Store(private var device: RegisteredDevice) : DeviceRegistryStore {
        override fun find(fingerprint: String): RegisteredDevice? = device.takeIf { it.fingerprint == fingerprint }
        override fun createPending(device: RegisteredDevice): Boolean = false
        override fun updateState(fingerprint: String, state: DeviceState, at: Instant): Boolean = false
    }

    private class ChallengeStoreImpl(private val challenge: IssuedDeviceChallenge) : ChallengeStore {
        var consumed = false
        override fun find(challengeId: String): IssuedDeviceChallenge? = challenge.takeIf { it.id == challengeId }
        override fun consume(challengeId: String): Boolean {
            if (consumed || challenge.id != challengeId) return false
            consumed = true
            return true
        }
    }
}
