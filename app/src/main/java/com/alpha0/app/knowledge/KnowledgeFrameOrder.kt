package com.alpha0.app.knowledge

/** Service consumer defense, never an identity attestor. Wall timestamps and
 * OCR cannot substitute for the exact source/session binding. A replay of the
 * same immutable frame may be rendered until expiry, but reordered or changed
 * results for that frame cannot become fresh evidence. */
internal class KnowledgeFrameOrder {
    private var epoch: Long? = null
    private var last: TrustedKnowledgeObservation? = null
    private var lastNow = -1L

    @Synchronized fun accepts(operation: Long, value: TrustedKnowledgeObservation, now: Long, maxAge: Long): Boolean {
        if (epoch != operation) { epoch = operation; last = null; lastNow = -1 }
        if (now < 0 || now < lastNow || value.frameSequence <= 0 || value.frameId.isBlank() ||
            value.frameCapturedMonotonicMs < 0 || value.ocrCompletedMonotonicMs < value.frameCapturedMonotonicMs ||
            value.observedMonotonicMs != value.ocrCompletedMonotonicMs || value.ocrCompletedMonotonicMs > now ||
            now - value.frameCapturedMonotonicMs > maxAge) return false
        val previous = last
        if (previous != null) {
            if (value.binding != previous.binding || value.sourceId != previous.sourceId) return false
            if (value.frameSequence < previous.frameSequence || value.observedAtMs < previous.observedAtMs ||
                value.frameCapturedMonotonicMs < previous.frameCapturedMonotonicMs ||
                value.ocrCompletedMonotonicMs < previous.ocrCompletedMonotonicMs) return false
            if (value.frameSequence == previous.frameSequence && value != previous) return false
            if (value.frameSequence > previous.frameSequence && (value.frameId == previous.frameId ||
                    value.frameCapturedMonotonicMs <= previous.frameCapturedMonotonicMs)) return false
        }
        last = value.copy(signals = value.signals.toMap()); lastNow = now
        return true
    }
}
