package com.alpha0.app.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class IntegrityPolicyTest {
    @Test
    fun strongAllowsCriticalActions() {
        assertTrue(IntegrityPolicy.allows(IntegrityTier.MEETS_STRONG_INTEGRITY, "device:rotate"))
    }

    @Test
    fun deviceIntegrityBlocksCriticalActions() {
        assertFalse(IntegrityPolicy.allows(IntegrityTier.MEETS_DEVICE_INTEGRITY, "device:rotate"))
        assertTrue(IntegrityPolicy.allows(IntegrityTier.MEETS_DEVICE_INTEGRITY, "game:read"))
    }

    @Test
    fun basicAndFailedDenyProtectedOperations() {
        assertTrue(IntegrityPolicy.allows(IntegrityTier.MEETS_BASIC_INTEGRITY, "character:read"))
        assertFalse(IntegrityPolicy.allows(IntegrityTier.MEETS_BASIC_INTEGRITY, "event:write"))
        assertFalse(IntegrityPolicy.allows(IntegrityTier.FAILED, "game:read"))
        assertFalse(IntegrityPolicy.allows(IntegrityTier.UNKNOWN, "game:read"))
    }
}
