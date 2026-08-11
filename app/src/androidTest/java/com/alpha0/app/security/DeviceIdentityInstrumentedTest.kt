package com.alpha0.app.security

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeviceIdentityInstrumentedTest {
    @Test
    fun generatesStableP256IdentityAndSigns() {
        val identity = DeviceIdentity()
        val first = identity.getIdentityInfo()
        val second = identity.getIdentityInfo()
        assertEquals(first.fingerprint, second.fingerprint)
        assertTrue(first.algorithm.contains("secp256r1"))
        assertTrue(identity.sign("sentinel-challenge".toByteArray()).isNotEmpty())
    }
}
