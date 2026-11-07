package com.alpha0.app.knowledge

/** Service consumer defense, never an identity attestor. Wall timestamps and
 * OCR cannot substitute for the exact source/session binding. A replay of the
 * same immutable frame may be rendered until expiry, but reordered or changed
 * results for that frame cannot become fresh evidence. */
internal class KnowledgeFrameOrder {
    private var epoch: Long? = null
    private var last: TrustedKnowledgeObservation? = null
    private var lastNow = -1L
    private var blocked = false

    @Synchronized fun reject(operation: Long) {
        if (epoch != null && operation < epoch!!) return
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1 }
        blocked = true
    }

    @Synchronized fun isBlocked(operation: Long): Boolean = epoch == operation && blocked

    @Synchronized fun rejectMissingAfterObservation(operation: Long) {
        if (epoch == operation && last != null) blocked = true
    }

    @Synchronized fun accepts(operation: Long, value: TrustedKnowledgeObservation, now: Long, maxAge: Long): Boolean {
        if (epoch != null && operation < epoch!!) return false
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1; blocked = false }
        if (blocked) return false
        fun deny(): Boolean { blocked = true; return false }
        if (now < 0 || now < lastNow || value.frameSequence <= 0 || value.frameId.isBlank() || value.frameId.length > 128 || value.sourceId != value.binding.sourceId ||
            value.frameCapturedMonotonicMs < 0 || value.ocrCompletedMonotonicMs < value.frameCapturedMonotonicMs ||
            value.observedMonotonicMs != value.ocrCompletedMonotonicMs || value.ocrCompletedMonotonicMs > now ||
            now - value.frameCapturedMonotonicMs > maxAge) return deny()
        val previous = last
        if (previous != null) {
            if (value.binding != previous.binding || value.sourceId != previous.sourceId) return deny()
            if (value.frameSequence < previous.frameSequence || value.observedAtMs < previous.observedAtMs ||
                value.frameCapturedMonotonicMs < previous.frameCapturedMonotonicMs ||
                value.ocrCompletedMonotonicMs < previous.ocrCompletedMonotonicMs) return deny()
            if (value.frameSequence == previous.frameSequence && value != previous) return deny()
            if (value.frameSequence > previous.frameSequence && (value.frameId == previous.frameId ||
                    value.frameCapturedMonotonicMs <= previous.frameCapturedMonotonicMs)) return deny()
        }
        last = value.copy(signals = value.signals.toMap()); lastNow = now
        return true
    }
}
