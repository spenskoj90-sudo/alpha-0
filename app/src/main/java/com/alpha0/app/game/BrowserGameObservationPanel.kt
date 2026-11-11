package com.alpha0.app.game

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alpha0.app.ui.DangerButton
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge

/**
 * LastHavens is a distinct browser target, NOT an alias for the Shattered OCR
 * pipeline. Opening a page supplies neither Chrome-tab proof nor game authority.
 * No MediaProjection consent, input executor, raw frames or OCR are shared here.
 */
@Composable
internal fun BrowserGameObservationPanel(
    onReturnToShattered: () -> Unit,
    onOpenOfficialUrl: (String) -> Boolean,
    stopLatch: GameAutomationStopLatch = GameAutomationStopRuntime.latch,
) {
    val strings = LocalAppStrings.current
    val target = BrowserGameSourcePolicy.LASTHAVENS
    val latched by stopLatch.state.collectAsStateWithLifecycle()
    var requested by remember { mutableStateOf(GameAutomationMode.OFF) }
    var riskAcknowledged by remember { mutableStateOf(false) }
    var rulesReviewed by remember { mutableStateOf(false) }
    var openFailed by remember { mutableStateOf(false) }
    val evidence = GameAutomationEvidence(
        riskAcknowledged = riskAcknowledged,
        operatorRulesReviewed = rulesReviewed,
        // No production Chrome-tab attestation exists. A user toggle or an
        // external ACTION_VIEW cannot establish source/action-grade evidence.
        stopLatched = latched.latched,
    )
    val decision = GameAutomationModePolicy.evaluate(requested, enabled = false, evidence)
    val preview = GameAutomationModePolicy.evaluate(requested, enabled = true, evidence)
    fun stopAutomation() {
        stopLatch.stop(null)
        requested = GameAutomationMode.OFF
        riskAcknowledged = false
        rulesReviewed = false
    }
    fun open(url: String) {
        stopAutomation()
        openFailed = !onOpenOfficialUrl(url)
    }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP) {
                // Backgrounding or opening Chrome invalidates every user choice;
                // the browser itself never reports trusted window identity here.
                stopAutomation()
            }
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }

    Scaffold(
        bottomBar = {
            DangerButton(
                strings.text("game_automation_stop"),
                { stopAutomation() },
                Modifier.fillMaxWidth().navigationBarsPadding().imePadding()
                    .padding(horizontal = 20.dp, vertical = 8.dp)
                    .testTag("game-automation-stop"),
            )
        },
    ) { insets ->
        Column(
            Modifier.fillMaxSize().padding(insets).verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(strings.text("game_browser_profile_title"), style = MaterialTheme.typography.headlineLarge)
            SecondaryButton(
                strings.text("game_browser_profile_return"),
                { stopAutomation(); onReturnToShattered() },
                Modifier.fillMaxWidth().testTag("game-browser-return"),
            )
            SentinelCard(kind = SentinelCardKind.CONTENT) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    StatusBadge(
                        strings.text("game_browser_source_unverified"),
                        SentinelStatus.WARNING,
                        Modifier.testTag("game-browser-source-status"),
                    )
                    Text(
                        strings.text("game_browser_profile_blocked"),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.testTag("game-browser-source-detail"),
                    )
                    Text(strings.text("game_browser_profile_source"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(strings.text("game_browser_profile_rules"), color = MaterialTheme.colorScheme.error)
                    SecondaryButton(
                        strings.text("game_browser_profile_open_game"),
                        { open(target.exactHttpsUrl) },
                        Modifier.fillMaxWidth().testTag("game-browser-open"),
                    )
                    SecondaryButton(
                        strings.text("game_browser_profile_open_rules"),
                        { open("https://lasthavens.com/terms") },
                        Modifier.fillMaxWidth().testTag("game-browser-rules"),
                    )
                    if (openFailed) Text(
                        strings.text("game_browser_profile_open_failed"),
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.testTag("game-browser-open-error"),
                    )
                }
            }
            GameAutomationModeControls(
                desiredMode = requested,
                onModeChange = { requested = it },
                riskAcknowledged = riskAcknowledged,
                onRiskAcknowledged = { riskAcknowledged = it },
                rulesReviewed = rulesReviewed,
                onRulesReviewed = { rulesReviewed = it },
                decision = decision,
                preview = preview,
                stopLatched = latched.latched,
                canResetStop = false,
                onEnable = {},
                onResetStop = {},
                scopeKey = "game_automation_scope_browser",
            )
        }
    }
}
