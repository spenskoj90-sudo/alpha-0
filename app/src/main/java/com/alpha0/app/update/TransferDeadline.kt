package com.alpha0.app.update

import java.io.IOException

/** Total elapsed network deadline, complementing per-read socket timeouts.
 * A monotonic regression or slow trickle must fail closed, never extend a transfer. */
internal class TransferDeadline(private val clock: () -> Long, timeoutMs: Long) {
    private val started = clock()
    private val duration = timeoutMs
    init { require(started >= 0 && duration in 1..1_800_000L) }

    fun check() {
        val now = clock()
        if (now < started || now - started >= duration) throw IOException("NETWORK_TRANSFER_DEADLINE")
    }
}
