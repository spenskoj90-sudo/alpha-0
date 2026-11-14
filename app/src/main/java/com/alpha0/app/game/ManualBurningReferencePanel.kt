package com.alpha0.app.game

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.politeStatusSemantics

/** Source-reviewed manual hypothesis; never an OCR source or game-action grant. */
@Composable
internal fun ManualBurningReferencePanel(
    installed: StockGameInstall?,
    captureId: String?,
    captureActive: Boolean,
) {
    val strings = LocalAppStrings.current
    val supported = installed?.versionName == "4.0.2" && installed.versionCode == 922L
    var expanded by remember(installed, captureId, captureActive) { mutableStateOf(false) }
    var burning by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    var flying by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    var water by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    var safe by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }

    SentinelCard(kind = SentinelCardKind.CONTENT) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(strings.text("game_manual_burn_title"), style = MaterialTheme.typography.titleMedium)
            Text(strings.text("game_manual_burn_disclosure"),
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            when {
                !supported -> Text(strings.text("game_manual_burn_unsupported"),
                    Modifier.testTag("game-manual-burn-result"))
                captureActive -> Text(strings.text("game_manual_burn_paused"),
                    Modifier.testTag("game-manual-burn-result"))
                else -> {
                    SecondaryButton(strings.text(if (expanded) "game_manual_burn_hide"
                        else "game_manual_burn_show"), { expanded = !expanded },
                        Modifier.fillMaxWidth().testTag("game-manual-burn-toggle"))
                    if (expanded) {
                        ManualFactQuestion(strings.text("game_manual_burn_burning"), "burn-burning", burning) { burning = it }
                        ManualFactQuestion(strings.text("game_manual_burn_flying"), "burn-flying", flying) { flying = it }
                        ManualFactQuestion(strings.text("game_manual_burn_water"), "burn-water", water) { water = it }
                        ManualFactQuestion(strings.text("game_manual_burn_safe"), "burn-safe", safe) { safe = it }
                        val outcome = ShatteredManualBurning.evaluate(
                            installed?.versionName, installed?.versionCode, burning, flying, water, safe)
                        val message = when (outcome) {
                            ShatteredManualBurning.Outcome.FLYING_EXCEPTION -> "game_manual_burn_flying_exception"
                            ShatteredManualBurning.Outcome.IN_WATER_MAY_EXTINGUISH -> "game_manual_burn_in_water"
                            ShatteredManualBurning.Outcome.POSSIBLE_SAFE_WATER_ROUTE -> "game_manual_burn_possible_water"
                            ShatteredManualBurning.Outcome.NO_CONFIRMED_SAFE_WATER -> "game_manual_burn_no_safe"
                            ShatteredManualBurning.Outcome.NO_BURNING -> "game_manual_burn_no_burn"
                            else -> "game_manual_burn_unknown"
                        }
                        Text(strings.text(message), Modifier.testTag("game-manual-burn-result")
                            .politeStatusSemantics(), color = MaterialTheme.colorScheme.onSurface)
                        Text(strings.text("game_manual_burn_caveat"),
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        SecondaryButton(strings.text("game_manual_reset"), {
                            burning = ShatteredManualHealing.Answer.UNKNOWN
                            flying = ShatteredManualHealing.Answer.UNKNOWN
                            water = ShatteredManualHealing.Answer.UNKNOWN
                            safe = ShatteredManualHealing.Answer.UNKNOWN
                        }, Modifier.fillMaxWidth().testTag("game-manual-burn-reset"),
                            enabled = listOf(burning, flying, water, safe).any {
                                it != ShatteredManualHealing.Answer.UNKNOWN
                            })
                    }
                }
            }
        }
    }
}
