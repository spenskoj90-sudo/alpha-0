package com.alpha0.app.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ReplayProtectionTest {
    @Test
    fun challengeIsOneTime() {
        val protection = ReplayProtection()
        assertTrue(protection.accept("nonce-1", 1000, 1000))
        assertFalse(protection.accept("nonce-1", 1000, 1000))
    }

    @Test
    fun staleChallengeIsRejected() {
        val protection = ReplayProtection()
        assertFalse(protection.accept("nonce-2", 1000, 1300))
    }
}
