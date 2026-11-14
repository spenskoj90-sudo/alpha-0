package com.alpha0.app.knowledge

/** Service consumer defense, never an identity attestor. Wall timestamps and
 * OCR cannot substitute for the exact source/session binding. A replay of the
 * same immutable frame may be rendered until expiry, but reordered or changed
 * results for that frame cannot become fresh evidence. */
internal class KnowledgeFrameOrder {
    private var epoch: Long? = null
    private var last: TrustedKnowledgeObservation? = null
    private var lastNow = -1L
    private var pending: Pair<Long, Long>? = null
    private var blocked = false

    @Synchronized fun reject(operation: Long) {
        if (epoch != null && operation < epoch!!) return
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1; pending = null }
        blocked = true
    }

    @Synchronized fun isBlocked(operation: Long): Boolean = epoch == operation && blocked

    @Synchronized fun rejectMissingAfterObservation(operation: Long) {
        if (epoch == operation && (last != null || pending != null)) blocked = true
    }

    /** In-flight identity is bounded; it never permits reusing previously displayed advice. */
    @Synchronized fun processing(operation: Long, sequence: Long, captured: Long, now: Long, maxAge: Long): Boolean {
        if (epoch != null && operation < epoch!!) return false
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1; pending = null; blocked = false }
        if (blocked) return false
        fun deny(): Boolean { blocked = true; return false }
        if (sequence <= 0 || captured < 0 || now < captured || now - captured > minOf(maxAge, 5000L) || now < lastNow) return deny()
        val previous = last
        if (previous != null && (sequence <= previous.frameSequence || captured <= previous.frameCapturedMonotonicMs)) return deny()
        val requested = sequence to captured
        if (pending != null && pending != requested) return deny()
        pending = requested
        lastNow = now
        return true
    }
    @Synchronized fun accepts(operation: Long, value: TrustedKnowledgeObservation, now: Long, maxAge: Long): Boolean {
        if (epoch != null && operation < epoch!!) return false
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1; pending = null; blocked = false }
        if (blocked) return false
        fun deny(): Boolean { blocked = true; return false }
        if (now < 0 || now < lastNow || value.frameSequence <= 0 || value.frameId.isBlank() || value.frameId.length > 128 || value.sourceId != value.binding.sourceId ||
            value.frameCapturedMonotonicMs < 0 || value.ocrCompletedMonotonicMs < value.frameCapturedMonotonicMs ||
            value.observedMonotonicMs != value.ocrCompletedMonotonicMs || value.ocrCompletedMonotonicMs > now ||
            now - value.frameCapturedMonotonicMs > maxAge) return deny()
        val previous = last
        // A new frame cannot bypass the five-second OCR deadline merely because
        // its Processing phase was not polled. An immutable previously accepted
        // frame may still be re-rendered until its separate pack age expires.
        if ((pending != null || previous == null || value.frameSequence > previous.frameSequence) &&
            now - value.frameCapturedMonotonicMs > minOf(maxAge, 5000L)) return deny()
        if (pending != null && pending != (value.frameSequence to value.frameCapturedMonotonicMs)) return deny()
        if (previous != null) {
            if (value.binding != previous.binding || value.sourceId != previous.sourceId) return deny()
            if (value.frameSequence < previous.frameSequence || value.observedAtMs < previous.observedAtMs ||
                value.frameCapturedMonotonicMs < previous.frameCapturedMonotonicMs ||
                value.ocrCompletedMonotonicMs < previous.ocrCompletedMonotonicMs) return deny()
            if (value.frameSequence == previous.frameSequence && value != previous) return deny()
            if (value.frameSequence > previous.frameSequence && (value.frameId == previous.frameId ||
                    value.frameCapturedMonotonicMs <= previous.frameCapturedMonotonicMs)) return deny()
        }
        pending = null
        last = value.copy(signals = value.signals.toMap()); lastNow = now
        return true
    }
}
