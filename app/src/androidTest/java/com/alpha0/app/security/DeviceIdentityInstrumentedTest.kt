package com.alpha0.app.security

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeviceIdentityInstrumentedTest {
    @Test
    fun generatesStableP256IdentityAndSigns() {
        val identity = DeviceIdentity()
        identity.attachDiagnostics(InstrumentationRegistry.getInstrumentation().targetContext)
        val first = identity.getIdentityInfo()
        val second = identity.getIdentityInfo()
        assertEquals(first.fingerprint, second.fingerprint)
        assertTrue(first.algorithm.contains("secp256r1"))
        assertTrue(identity.sign("sentinel-challenge".toByteArray()).isNotEmpty())
    }

    @Test
    fun stagesAbortsAndCommitsHardwareBackedRotation() {
        val identity = DeviceIdentity()
        identity.attachDiagnostics(InstrumentationRegistry.getInstrumentation().targetContext)
        val original = identity.getIdentityInfo().fingerprint

        val aborted = identity.prepareRotation()
        assertNotEquals(original, aborted.fingerprint)
        assertEquals(aborted.fingerprint, DeviceIdentity().also {
            it.attachDiagnostics(InstrumentationRegistry.getInstrumentation().targetContext)
        }.pendingRotation()?.fingerprint)
        identity.abortRotation(aborted)
        assertEquals(original, identity.getIdentityInfo().fingerprint)
        assertEquals(null, identity.pendingRotation())

        val committed = identity.prepareRotation()
        assertEquals(committed.fingerprint, identity.pendingRotation()?.fingerprint)
        identity.commitRotation(committed)
        assertEquals(null, identity.pendingRotation())
        assertEquals(committed.fingerprint, identity.getIdentityInfo().fingerprint)
        assertNotEquals(original, committed.fingerprint)
        val challenge = "rotated-sentinel-challenge".toByteArray()
        val signature = identity.sign(challenge)
        assertTrue(identity.verify(challenge, signature))
    }
}
