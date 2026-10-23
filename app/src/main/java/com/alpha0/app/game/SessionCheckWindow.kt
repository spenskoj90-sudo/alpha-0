package com.alpha0.app.game

/**
 * Main-thread-owned guard for bounded asynchronous session checks.
 *
 * A late worker callback can never complete a newer check or revive a stopped
 * observation. This is lifecycle bookkeeping, not authorization by itself.
 */
internal class SessionCheckWindow(private val timeoutMs: Long = 10_000L) {
    init { require(timeoutMs > 0) }

    private var nextTicket = 0L
    private var pendingTicket: Long? = null
    private var startedAt = 0L

    fun begin(now: Long): Long? {
        if (now < 0 || pendingTicket != null) return null
        nextTicket += 1L
        pendingTicket = nextTicket
        startedAt = now
        return nextTicket
    }

    fun expired(now: Long): Boolean =
        pendingTicket != null && (now < startedAt || now - startedAt >= timeoutMs)

    fun complete(ticket: Long): Boolean {
        if (pendingTicket != ticket) return false
        pendingTicket = null
        return true
    }

    fun cancel() {
        pendingTicket = null
    }
}
