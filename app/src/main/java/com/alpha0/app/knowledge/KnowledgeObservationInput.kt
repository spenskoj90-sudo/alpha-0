package com.alpha0.app.knowledge

/** Service-owned observation phase; never inferred from OCR or UI assertions. */
internal sealed interface KnowledgeObservationInput {
    data object AwaitingFirstFrame : KnowledgeObservationInput
    data class Processing(val sequence: Long, val capturedMonotonicMs: Long) : KnowledgeObservationInput
    data class Frame(val value: TrustedKnowledgeObservation) : KnowledgeObservationInput
    data object Unavailable : KnowledgeObservationInput
}
