package com.alpha0.app.game

import android.app.Activity
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.SystemClock
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.OutlinedTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import com.alpha0.app.diagnostics.DiagnosticLogger
import java.util.UUID
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alpha0.app.BuildConfig
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge
import kotlinx.coroutines.delay

@Composable
fun GameObservationScreen() {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var installed by remember { mutableStateOf(ShatteredGameProfile.installed(context)) }
    val state by GameObservationRuntime.state.collectAsStateWithLifecycle()
    var consent by rememberSaveable { mutableStateOf(false) }
    var pendingVersion by rememberSaveable { mutableStateOf<Long?>(null) }
    var pending by rememberSaveable { mutableStateOf(false) }
    var elapsed by remember { mutableStateOf(SystemClock.elapsedRealtime()) }

    DisposableEffect(lifecycle, context) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) installed = ShatteredGameProfile.installed(context)
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(state.observation.lastHealth?.observedAt) {
        while (true) { elapsed = SystemClock.elapsedRealtime(); delay(1000) }
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        pending = false
        consent = false
        val expectedVersion = pendingVersion
        pendingVersion = null
        val currentInstall = ShatteredGameProfile.installed(context)
        val session = SecureSessionStore().load(context)
        when {
            result.resultCode != Activity.RESULT_OK || result.data == null -> GameObservationRuntime.stop("CONSENT_CANCELLED")
            expectedVersion == null || currentInstall?.versionCode != expectedVersion || session?.deviceId.isNullOrBlank() ->
                GameObservationRuntime.stop("SESSION_OR_GAME_UNAVAILABLE")
            else -> GameObservationService.start(context, result.data!!, currentInstall!!)
        }
    }
    GameObservationPanel(
        installed = installed,
        state = state,
        supported = BuildConfig.DEBUG && Build.VERSION.SDK_INT >= 34,
        consent = consent,
        pending = pending,
        now = elapsed,
        onConsent = { consent = it },
        onStart = {
            val current = ShatteredGameProfile.installed(context)
            if (current == null) {
                installed = null
                GameObservationRuntime.stop("SESSION_OR_GAME_UNAVAILABLE")
            } else {
                pendingVersion = current.versionCode
                pending = true
                try {
                    val manager = context.getSystemService(MediaProjectionManager::class.java)
                        ?: throw IllegalStateException("Projection service unavailable")
                    launcher.launch(manager.createScreenCaptureIntent())
                } catch (_: Exception) {
                    pending = false
                    pendingVersion = null
                    consent = false
                    GameObservationRuntime.stop("CAPTURE_START_FAILED")
                }
            }
        },
        onStop = { GameObservationService.stop(context); consent = false },
        onLaunch = {
            try {
                context.packageManager.getLaunchIntentForPackage(ShatteredGameProfile.PACKAGE)?.let(context::startActivity)
                    ?: GameObservationRuntime.stop("SESSION_OR_GAME_UNAVAILABLE")
            } catch (_: Exception) {
                GameObservationRuntime.stop("SESSION_OR_GAME_UNAVAILABLE")
            }
        },
    )
}

@Composable
internal fun GameObservationPanel(
    installed: StockGameInstall?,
    state: GameObservationViewState,
    supported: Boolean,
    consent: Boolean,
    pending: Boolean,
    now: Long,
    onConsent: (Boolean) -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onLaunch: () -> Unit,
) {
    val strings = LocalAppStrings.current
    val observation = state.observation
    val context = LocalContext.current
    val campaign = remember(state.installed ?: installed) { CalibrationCampaign() }
    val campaignId = remember(state.installed ?: installed) { UUID.randomUUID().toString() }
    var expectedCurrent by remember { mutableStateOf("") }
    var expectedMaximum by remember { mutableStateOf("") }
    var sampleCount by remember(state.installed ?: installed) { mutableStateOf(0) }
    var calibrationMessage by remember { mutableStateOf("") }
    val active = observation.status in setOf(ObservationStatus.WAITING, ObservationStatus.OBSERVING, ObservationStatus.PAUSED)
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(strings.text("game_observer_title"), style = MaterialTheme.typography.headlineLarge)
        Text("Shattered Pixel Dungeon", style = MaterialTheme.typography.titleLarge)
        Text(strings.text("game_observer_subtitle"), color = MaterialTheme.colorScheme.onSurfaceVariant)
        SentinelCard(kind = SentinelCardKind.CONTENT) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (installed == null) {
                    StatusBadge(strings.text("status_unavailable"), SentinelStatus.UNAVAILABLE)
                    Text(strings.text("game_install_missing"))
                } else {
                    Text(strings.text("game_install_version", installed.versionName, installed.versionCode))
                    Text(strings.text("game_capture_source_unverified"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    SecondaryButton(strings.text("game_capture_launch"), onLaunch, Modifier.fillMaxWidth())
                }
            }
        }
        SentinelCard(kind = SentinelCardKind.OPERATIONAL) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                val label = when (observation.status) {
                    ObservationStatus.WAITING -> "game_capture_waiting"
                    ObservationStatus.OBSERVING -> "game_capture_active"
                    ObservationStatus.PAUSED -> "game_capture_paused"
                    else -> "status_stopped"
                }
                StatusBadge(strings.text(label), when (observation.status) {
                    ObservationStatus.OBSERVING -> SentinelStatus.ACTIVE
                    ObservationStatus.WAITING -> SentinelStatus.PENDING
                    ObservationStatus.PAUSED -> SentinelStatus.WARNING
                    else -> SentinelStatus.STOPPED
                })
                Text(strings.text("game_capture_summary", observation.frames))
                when (observation.reason) {
                    "CONSENT_CANCELLED" -> Text(strings.text("game_capture_cancelled"))
                    "CAPTURE_START_FAILED", "CAPTURE_RESIZE_FAILED", "RECOGNITION_UNAVAILABLE", "INVALID_CAPTURE_SIZE", "SESSION_OR_GAME_UNAVAILABLE" ->
                        Text(strings.text("game_capture_failed"), color = MaterialTheme.colorScheme.error)
                    "TIME_LIMIT" -> Text(strings.text("game_capture_time_limit"))
                }
                if (active) {
                    PrimaryButton(strings.text("game_capture_stop"), onStop, Modifier.fillMaxWidth().testTag("game-capture-stop"))
                } else {
                    Text(strings.text("game_capture_disclosure"))
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 48.dp)
                            .toggleable(consent, enabled = supported && installed != null && !pending, role = Role.Checkbox, onValueChange = onConsent),
                    ) {
                        Checkbox(consent, onCheckedChange = null, enabled = supported && installed != null && !pending)
                        Text(strings.text("game_capture_consent"), Modifier.padding(top = 12.dp))
                    }
                    PrimaryButton(
                        strings.text(if (pending) "game_capture_waiting" else "game_capture_start"), onStart,
                        Modifier.fillMaxWidth().testTag("game-capture-start"),
                        enabled = supported && installed != null && consent && !pending,
                    )
                    if (!supported) Text(strings.text("game_capture_android14"))
                }
            }
        }
        observation.lastHealth?.let { last ->
            SentinelCard(kind = SentinelCardKind.CONTENT) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    DataText("INFERENCE")
                    Text(strings.text("game_capture_health", last.candidate.current, last.candidate.maximum, last.candidate.shield))
                    Text(strings.text("game_capture_age", maxOf(0, (now - last.observedAt) / 1000)))
                    Text(strings.text("game_capture_hypothesis"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        SentinelCard(kind = SentinelCardKind.CONTENT) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(strings.text("game_calibration_title"), style = MaterialTheme.typography.titleMedium)
                StatusBadge(strings.text("game_calibration_pending"), SentinelStatus.PENDING)
                Text(strings.text("game_calibration_disclosure"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(expectedCurrent, { expectedCurrent = it.take(6) }, label = { Text(strings.text("game_calibration_current")) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(expectedMaximum, { expectedMaximum = it.take(6) }, label = { Text(strings.text("game_calibration_maximum")) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true, modifier = Modifier.fillMaxWidth())
                SecondaryButton(strings.text("game_calibration_save"), {
                    val sample = campaign.record(expectedCurrent, expectedMaximum, observation.lastHealth, now)
                    if (sample == null) calibrationMessage = "game_calibration_invalid"
                    else {
                        val sampleInstall = state.installed ?: installed
                        DiagnosticLogger.get(context).info("GAME", "CALIBRATION_NUMERIC_SAMPLE", "OBSERVED", details = mapOf(
                            "calibration_campaign" to campaignId, "sample_sequence" to sample.sequence,
                            "game_package" to ShatteredGameProfile.PACKAGE,
                            "game_version" to sampleInstall?.versionName, "game_version_code" to sampleInstall?.versionCode,
                            "age_ms" to sample.ageMs, "recognized_current" to sample.observed?.current,
                            "recognized_maximum" to sample.observed?.maximum,
                            "ground_truth_current" to sample.current, "ground_truth_maximum" to sample.maximum,
                                "source_status" to "UNVERIFIED", "sample_kind" to "user-opt-in",
                                "device_environment" to "UNVERIFIED",
                        ))
                        sampleCount = campaign.count
                        calibrationMessage = "game_calibration_saved"
                    }
                }, Modifier.fillMaxWidth(), enabled = supported && installed != null && (state.installed == null || state.installed == installed) && sampleCount < 32)
                Text(strings.text("game_calibration_count", sampleCount))
                if (calibrationMessage.isNotBlank()) Text(strings.text(calibrationMessage))
                Text(strings.text("game_calibration_action_gate"), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Text(strings.text("game_capture_boundary"), color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
