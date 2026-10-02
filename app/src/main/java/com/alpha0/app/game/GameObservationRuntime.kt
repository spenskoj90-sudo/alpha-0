package com.alpha0.app.game

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class GameObservationViewState(
    val observation: ObservationSnapshot = ObservationSnapshot(),
    val installed: StockGameInstall? = null,
)

/** Process-local state. Pixels, OCR text and health are never persisted or queued to Core. */
object GameObservationRuntime {
    internal val session = ObservationSession()
    private val mutableState = MutableStateFlow(GameObservationViewState())
    val state = mutableState.asStateFlow()

    internal fun begin(install: StockGameInstall, id: String, now: Long) {
        session.start(id, now)
        mutableState.value = GameObservationViewState(session.snapshot, install)
    }

    internal fun publish() {
        mutableState.value = mutableState.value.copy(observation = session.snapshot)
    }

    internal fun stop(reason: String) {
        session.stop(reason)
        publish()
    }
}
