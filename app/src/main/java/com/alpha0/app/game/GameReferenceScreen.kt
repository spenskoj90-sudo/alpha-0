package com.alpha0.app.game

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alpha0.app.ui.LocalAppStrings

/** Read-only game rule reference, accessible even when screen capture is off. */
@Composable
fun GameReferenceScreen() {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var installed by remember(context) { mutableStateOf(ShatteredGameProfile.installed(context)) }
    DisposableEffect(context, lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                installed = ShatteredGameProfile.installed(context)
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    // A capture started from the observer route survives navigation; the
    // reference route must not silently reset the shared manual-input guard.
    val runtime by GameObservationRuntime.state.collectAsStateWithLifecycle()
    val observation = runtime.observation
    GameReferencePanel(
        installed, observation.captureId,
        observation.status in setOf(ObservationStatus.WAITING, ObservationStatus.OBSERVING, ObservationStatus.PAUSED),
    )
}

/** Injectable local UI for tests; never enables projection, OCR or game input. */
@Composable
internal fun GameReferencePanel(
    installed: StockGameInstall?,
    captureId: String? = null,
    captureActive: Boolean = false,
) {
    val strings = LocalAppStrings.current
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(strings.text("game_reference_title"), style = MaterialTheme.typography.headlineLarge)
        Text("Shattered Pixel Dungeon", style = MaterialTheme.typography.titleMedium)
        Text(strings.text("game_reference_disclosure"),
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (installed == null) {
            Text(strings.text("game_install_missing"))
        } else {
            Text(strings.text("game_install_version", installed.versionName, installed.versionCode))
        }
        ManualHealingReferencePanel(installed, captureId, captureActive)
        ManualBurningReferencePanel(installed, captureId, captureActive)
    }
}
