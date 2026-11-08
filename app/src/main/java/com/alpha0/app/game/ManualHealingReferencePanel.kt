package com.alpha0.app.game

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
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

/** Only source-reviewed facts about a manually entered hypothetical scenario.
 * No OCR, online session, privileged game interface, persistent state or action. */
@Composable
internal fun ManualHealingReferencePanel(
    installed: StockGameInstall?,
    captureId: String?,
    captureActive: Boolean,
) {
    val strings = LocalAppStrings.current
    // Revoke all self-reported facts across app/version/capture transitions.
    var lowHealth by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    var pharmacophobia by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    var knownPotion by remember(installed, captureId, captureActive) {
        mutableStateOf(ShatteredManualHealing.Answer.UNKNOWN)
    }
    val supported = installed?.versionName == "4.0.2" && installed.versionCode == 922L

    SentinelCard(kind = SentinelCardKind.CONTENT) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(strings.text("game_manual_title"), style = MaterialTheme.typography.titleMedium)
            Text(strings.text("game_manual_disclosure"),
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            when {
                !supported -> Text(strings.text("game_manual_unsupported"),
                    Modifier.testTag("game-manual-result"))
                captureActive -> Text(strings.text("game_manual_paused"),
                    Modifier.testTag("game-manual-result"))
                else -> {
                    ManualFactQuestion(strings.text("game_manual_low"), "low", lowHealth) { lowHealth = it }
                    ManualFactQuestion(strings.text("game_manual_pharma"), "pharma", pharmacophobia) { pharmacophobia = it }
                    ManualFactQuestion(strings.text("game_manual_potion"), "potion", knownPotion) { knownPotion = it }
                    val outcome = ShatteredManualHealing.evaluate(
                        installed.versionName, installed.versionCode,
                        lowHealth, pharmacophobia, knownPotion,
                    )
                    val key = when (outcome) {
                        ShatteredManualHealing.Outcome.POISON_WARNING -> "game_manual_poison"
                        ShatteredManualHealing.Outcome.POSSIBLE_OPTION -> "game_manual_option"
                        ShatteredManualHealing.Outcome.NO_RULE_MATCH -> "game_manual_no_rule"
                        else -> "game_manual_unknown"
                    }
                    Text(strings.text(key), Modifier.testTag("game-manual-result")
                        .politeStatusSemantics(), color = MaterialTheme.colorScheme.onSurface)
                    Text(strings.text("game_manual_reason"),
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                    SecondaryButton(strings.text("game_manual_reset"), {
                        lowHealth = ShatteredManualHealing.Answer.UNKNOWN
                        pharmacophobia = ShatteredManualHealing.Answer.UNKNOWN
                        knownPotion = ShatteredManualHealing.Answer.UNKNOWN
                    }, Modifier.fillMaxWidth().testTag("game-manual-reset"), enabled =
                        lowHealth != ShatteredManualHealing.Answer.UNKNOWN ||
                        pharmacophobia != ShatteredManualHealing.Answer.UNKNOWN ||
                        knownPotion != ShatteredManualHealing.Answer.UNKNOWN)
                }
            }
        }
    }
}

@Composable
private fun ManualFactQuestion(
    title: String,
    id: String,
    value: ShatteredManualHealing.Answer,
    onSelect: (ShatteredManualHealing.Answer) -> Unit,
) {
    val strings = LocalAppStrings.current
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title)
        // Horizontally scrollable at 200% font scale, never truncate the answer.
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for (choice in ShatteredManualHealing.Answer.entries) {
                val option = when (choice) {
                    ShatteredManualHealing.Answer.UNKNOWN -> "game_manual_answer_unknown"
                    ShatteredManualHealing.Answer.YES -> "game_manual_answer_yes"
                    ShatteredManualHealing.Answer.NO -> "game_manual_answer_no"
                }
                FilterChip(
                    selected = value == choice, onClick = { onSelect(choice) },
                    label = { Text(strings.text(option)) },
                    modifier = Modifier.testTag("game-manual-$id-${choice.name.lowercase()}"),
                )
            }
        }
    }
}
