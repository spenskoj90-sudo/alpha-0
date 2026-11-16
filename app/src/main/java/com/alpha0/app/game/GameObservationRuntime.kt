package com.alpha0.app.game

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class GameObservationViewState(
    val observation: ObservationSnapshot = ObservationSnapshot(),
    val installed: StockGameInstall? = null,
)

/** Process-local state. Pixels/raw OCR are never persisted or queued to Core.
 * Numeric calibration pairs require a separate explicit user Save in the diagnostics panel.
 */
object GameObservationRuntime {
    internal val session = ObservationSession()
    internal val calibration = CalibrationCampaignRegistry()
    private val mutableState = MutableStateFlow(GameObservationViewState())
    val state = mutableState.asStateFlow()

    internal fun begin(install: StockGameInstall, id: String, now: Long) {
        com.alpha0.app.knowledge.AndroidKnowledgeRuntime.start()
        calibration.clear()
        session.start(id, now)
        // Only a real new capture generation can unlock an explicit Stop reset.
        // This is not source attestation, input authority or an automatic reset.
        GameAutomationStopRuntime.latch.onCaptureStarted(id)
        mutableState.value = GameObservationViewState(session.snapshot, install)
    }

    internal fun publish() {
        mutableState.value = mutableState.value.copy(observation = session.snapshot)
    }

    internal fun stop(reason: String) {
        // Revoke any action authority before the capture generation is cleared.
        GameAutomationStopRuntime.latch.stop(session.snapshot.captureId)
        com.alpha0.app.knowledge.AndroidKnowledgeRuntime.stop()
        session.stop(reason)
        calibration.clear()
        publish()
    }
}
