package com.alpha0.app.dashboard

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DashboardSecurityStateTest {
    @Test
    fun activeSecureDeviceIsTrusted() {
        assertTrue(isTrustedDeviceState("ACTIVE", "SECURE"))
        assertTrue(isTrustedDeviceState("active", "ok"))
    }

    @Test
    fun nonActiveOrNonSecureDeviceRequiresAttention() {
        assertFalse(isTrustedDeviceState("REVOKED", "SECURE"))
        assertFalse(isTrustedDeviceState("ACTIVE", "AT_RISK"))
        assertFalse(isTrustedDeviceState(null, "SECURE"))
    }
}
