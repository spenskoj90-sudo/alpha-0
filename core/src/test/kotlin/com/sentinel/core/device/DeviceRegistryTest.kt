package com.sentinel.core.device

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.time.Instant

class DeviceRegistryTest {
    private val now = Instant.parse("2026-08-10T12:00:00Z")
    private val keyPair = KeyPairGenerator.getInstance("EC").apply { initialize(256) }.generateKeyPair()
    private val publicKey = keyPair.public.encoded
    private val fingerprint = MessageDigest.getInstance("SHA-256").digest(publicKey)
        .joinToString("") { "%02x".format(it.toInt() and 0xff) }

    @Test
    fun registrationStartsPendingAndDoesNotGrantActiveState() {
        val store = MemoryStore()
        val registry = DeviceRegistry(store) { now }
        val result = registry.registerPending(fingerprint, publicKey)
        assertTrue(result is DeviceRegistryResult.Registered)
        assertFalse(registry.isActive(fingerprint))
    }

    @Test
    fun activationMovesPendingToActive() {
        val store = MemoryStore()
        val registry = DeviceRegistry(store) { now }
        registry.registerPending(fingerprint, publicKey)
        val result = registry.activate(fingerprint)
        assertEquals(DeviceRegistryResult.Activated(store.devices[fingerprint]!!.copy(updatedAt = now)), result)
        assertTrue(registry.isActive(fingerprint))
    }

    @Test
    fun revokedDeviceCannotBeActivated() {
        val store = MemoryStore()
        val registry = DeviceRegistry(store) { now }
        registry.registerPending(fingerprint, publicKey)
        store.devices[fingerprint] = store.devices[fingerprint]!!.copy(state = DeviceState.REVOKED)
        assertEquals(DeviceRegistryResult.Rejected(DeviceRegistryFailure.REVOKED), registry.activate(fingerprint))
        assertFalse(registry.isActive(fingerprint))
    }

    @Test
    fun fingerprintMustMatchPublicKey() {
        val registry = DeviceRegistry(MemoryStore()) { now }
        assertEquals(
            DeviceRegistryResult.Rejected(DeviceRegistryFailure.MALFORMED_REQUEST),
            registry.registerPending("a".repeat(64), publicKey)
        )
    }

    @Test
    fun malformedFingerprintIsRejected() {
        val registry = DeviceRegistry(MemoryStore()) { now }
        assertEquals(
            DeviceRegistryResult.Rejected(DeviceRegistryFailure.MALFORMED_REQUEST),
            registry.registerPending("bad", publicKey)
        )
    }

    @Test
    fun storeFailureFailsClosed() {
        val store = object : DeviceRegistryStore {
            override fun find(fingerprint: String): RegisteredDevice? = error("db unavailable")
            override fun createPending(device: RegisteredDevice): Boolean = error("db unavailable")
            override fun updateState(fingerprint: String, state: DeviceState, at: Instant): Boolean = error("db unavailable")
        }
        val registry = DeviceRegistry(store) { now }
        assertEquals(
            DeviceRegistryResult.Rejected(DeviceRegistryFailure.STORE_UNAVAILABLE),
            registry.registerPending(fingerprint, publicKey)
        )
        assertFalse(registry.isActive(fingerprint))
    }

    private class MemoryStore : DeviceRegistryStore {
        val devices = mutableMapOf<String, RegisteredDevice>()
        override fun find(fingerprint: String): RegisteredDevice? = devices[fingerprint]
        override fun createPending(device: RegisteredDevice): Boolean = devices.putIfAbsent(device.fingerprint, device) == null
        override fun updateState(fingerprint: String, state: DeviceState, at: Instant): Boolean {
            val existing = devices[fingerprint] ?: return false
            devices[fingerprint] = existing.copy(state = state, updatedAt = at)
            return true
        }
    }
}
