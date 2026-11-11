package com.alpha0.app.game

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal data class GameAutomationStopState(
    val latched: Boolean = false,
    /** Capture generation for which STOP was latched; never persists across process death. */
    val stoppedCaptureId: String? = null,
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
        )
    }

    @Synchronized
    fun canResetForNewCapture(captureId: String?): Boolean =
        mutable.value.let { current ->
            current.latched && !captureId.isNullOrBlank() &&
                captureId != current.stoppedCaptureId
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
