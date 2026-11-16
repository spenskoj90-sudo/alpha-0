package com.alpha0.app.game

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal data class GameAutomationStopState(
    val latched: Boolean = false,
    /** Capture generation for which STOP was latched; never persists across process death. */
    val stoppedCaptureId: String? = null,
    /** Non-authoritative reset token: observed only when the service starts a NEW capture. */
    val freshCaptureId: String? = null,
)

/**
 * Process-local STOP registry shared across Compose recreations and capture service callbacks.
 * A STOP cannot be cleared for the same capture generation; a fresh capture still needs
 * explicit user reset, fresh target proof and fresh action consent. This does not authorize input.
 */
internal class GameAutomationStopLatch {
    private val mutable = MutableStateFlow(GameAutomationStopState())
    val state = mutable.asStateFlow()

    @Synchronized
    fun stop(captureId: String?) {
        val previous = mutable.value
        mutable.value = GameAutomationStopState(
            latched = true,
            stoppedCaptureId = captureId?.takeIf { it.isNotBlank() } ?: previous.stoppedCaptureId,
            // Any STOP, including one without a capture ID, revokes prior reset eligibility.
            freshCaptureId = null,
        )
    }

    /** Called only by the capture service after an actual ObservationSession.start. */
    @Synchronized
    fun onCaptureStarted(captureId: String) {
        require(captureId.isNotBlank() && captureId.length <= 64)
        val current = mutable.value
        if (current.latched && captureId != current.stoppedCaptureId) {
            mutable.value = current.copy(freshCaptureId = captureId)
        }
    }

    @Synchronized
    fun canResetForNewCapture(captureId: String?): Boolean =
        mutable.value.let { current ->
            current.latched && !captureId.isNullOrBlank() &&
                captureId != current.stoppedCaptureId &&
                current.freshCaptureId == captureId
        }

    @Synchronized
    fun resetForNewCapture(captureId: String?): Boolean {
        if (!canResetForNewCapture(captureId)) return false
        mutable.value = GameAutomationStopState()
        return true
    }
}

internal object GameAutomationStopRuntime {
    val latch = GameAutomationStopLatch()
}
