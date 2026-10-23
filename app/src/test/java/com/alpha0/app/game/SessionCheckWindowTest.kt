package com.alpha0.app.game

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionCheckWindowTest {
    @Test fun `session check has bounded deadline and cannot overlap`() {
        val window = SessionCheckWindow(timeoutMs = 10_000L)
        val first = requireNotNull(window.begin(100))
        assertNull(window.begin(101))
        assertFalse(window.expired(10_099))
        assertTrue(window.expired(10_100))
        assertTrue(window.complete(first))
        assertFalse(window.expired(10_101))
    }

    @Test fun `cancelled and stale worker results cannot complete another check`() {
        val window = SessionCheckWindow()
        val old = requireNotNull(window.begin(100))
        window.cancel()
        assertFalse(window.complete(old))
        val current = requireNotNull(window.begin(200))
        assertFalse(window.complete(old))
        assertTrue(window.complete(current))
        assertFalse(window.complete(current))
    }

    @Test fun `reversed clock fails closed and invalid starting time is denied`() {
        val window = SessionCheckWindow()
        assertNull(window.begin(-1))
        val ticket = requireNotNull(window.begin(5_000))
        assertTrue(window.expired(4_999))
        assertTrue(window.complete(ticket))
    }
}
