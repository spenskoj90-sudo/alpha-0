package com.alpha0.app.game

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CaptureSessionFenceTest {
    @Test fun onlyTheAcknowledgedSessionMayStartOrContinueCapture() {
        val bound = CaptureSessionFence.snapshot("device-1", 12L)
        assertTrue(CaptureSessionFence.isCurrent(bound, "device-1", 12L))
        // In-principal token refresh via replaceIfCurrent retains the epoch.
        assertTrue(CaptureSessionFence.isCurrent(bound, "device-1", 12L))
        // A logout/login on the same device must not reuse earlier consent.
        assertFalse(CaptureSessionFence.isCurrent(bound, "device-1", 14L))
        assertFalse(CaptureSessionFence.isCurrent(bound, "device-2", 12L))
        assertFalse(CaptureSessionFence.isCurrent(bound, null, null))
        assertFalse(CaptureSessionFence.isCurrent(bound, "device-1", null))
    }

    @Test fun missingOrInvalidSnapshotAndIntentIdentityFailClosed() {
        assertNull(CaptureSessionFence.snapshot(null, 0L))
        assertNull(CaptureSessionFence.snapshot("", 0L))
        assertNull(CaptureSessionFence.snapshot("   ", 0L))
        assertNull(CaptureSessionFence.snapshot("device-1", null))
        assertNull(CaptureSessionFence.snapshot("device-1", -1L))
        assertFalse(CaptureSessionFence.isCurrent(null, "device-1", 12L))
        assertFalse(CaptureSessionFence.isCurrent(CaptureSessionFence.snapshot("device-1", 12L), "device-1", -1L))
    }

    @Test fun serviceRequiresPreciselyTheChooserSession() {
        val expected = CaptureSessionFence.snapshot("device-1", 42L)
        val serviceIntent = CaptureSessionFence.snapshot("device-1", 42L)
        assertTrue(CaptureSessionFence.isCurrent(serviceIntent, expected?.deviceId, expected?.epoch))
        assertFalse(CaptureSessionFence.isCurrent(serviceIntent, "device-1", 43L))
        assertFalse(CaptureSessionFence.isCurrent(
            CaptureSessionFence.snapshot("device-1", -1L), "device-1", 42L,
        ))
    }
}
