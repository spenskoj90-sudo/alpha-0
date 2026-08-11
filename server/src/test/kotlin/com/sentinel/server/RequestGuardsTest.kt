package com.sentinel.server

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import java.time.Duration
import java.time.Instant
import java.util.concurrent.atomic.AtomicReference

class RequestGuardsTest {
    @Test
    fun rateLimiterBoundsRequestsPerWindow() {
        val now = AtomicReference(Instant.parse("2026-01-01T00:00:00Z"))
        val limiter = SlidingWindowRateLimiter(2, Duration.ofMinutes(1)) { now.get() }
        assertTrue(limiter.allow("client"))
        assertTrue(limiter.allow("client"))
        assertFalse(limiter.allow("client"))
        now.set(now.get().plusSeconds(61))
        assertTrue(limiter.allow("client"))
    }

    @Test
    fun differentKeysDoNotShareQuota() {
        val limiter = SlidingWindowRateLimiter(1, Duration.ofMinutes(1))
        assertTrue(limiter.allow("a"))
        assertFalse(limiter.allow("a"))
        assertTrue(limiter.allow("b"))
    }

    @Test
    fun blankKeyIsRejected() {
        val limiter = SlidingWindowRateLimiter(1, Duration.ofMinutes(1))
        assertFalse(limiter.allow(""))
    }
}
