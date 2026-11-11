package com.alpha0.app.game

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge

@Composable
internal fun GameAutomationModeControls(
    desiredMode: GameAutomationMode,
    onModeChange: (GameAutomationMode) -> Unit,
    riskAcknowledged: Boolean,
    onRiskAcknowledged: (Boolean) -> Unit,
    rulesReviewed: Boolean,
    onRulesReviewed: (Boolean) -> Unit,
    decision: GameAutomationModeDecision,
    preview: GameAutomationModeDecision,
    stopLatched: Boolean,
    canResetStop: Boolean,
    onEnable: () -> Unit,
    onResetStop: () -> Unit,
    scopeKey: String = "game_automation_scope",
) {
    val strings = LocalAppStrings.current
    SentinelCard(kind = SentinelCardKind.CONTENT) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(strings.text("game_automation_title"), style = MaterialTheme.typography.titleMedium)
            Text(strings.text(scopeKey), color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(strings.text("game_automation_risk"), color = MaterialTheme.colorScheme.error)
            GameAutomationMode.entries.forEach { mode ->
                Row(
                    Modifier.fillMaxWidth()
                        .selectable(
                            selected = desiredMode == mode,
                            role = Role.RadioButton,
                            onClick = { onModeChange(mode) },
                        )
                        .testTag("game-automation-mode-${mode.name.lowercase()}"),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = desiredMode == mode, onClick = null)
                    Column(Modifier.weight(1f).padding(vertical = 4.dp)) {
                        Text(strings.text(mode.labelKey), style = MaterialTheme.typography.bodyLarge)
                        Text(strings.text(mode.descriptionKey), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            Row(
                Modifier.fillMaxWidth().testTag("game-automation-risk-ack-row"),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Checkbox(
                    checked = riskAcknowledged,
                    onCheckedChange = onRiskAcknowledged,
                    modifier = Modifier.testTag("game-automation-risk-ack"),
                )
                Text(strings.text("game_automation_risk_ack"))
            }
            Row(
                Modifier.fillMaxWidth().testTag("game-automation-rules-reviewed-row"),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Checkbox(
                    checked = rulesReviewed,
                    onCheckedChange = onRulesReviewed,
                    modifier = Modifier.testTag("game-automation-rules-reviewed"),
                )
                Text(strings.text("game_automation_rules_ack"))
            }
            StatusBadge(
                strings.text("game_automation_effective", strings.text(decision.effectiveMode.labelKey)),
                when {
                    decision.effectiveMode != GameAutomationMode.OFF -> SentinelStatus.ACTIVE
                    desiredMode != GameAutomationMode.OFF || stopLatched -> SentinelStatus.WARNING
                    else -> SentinelStatus.STOPPED
                },
                Modifier.testTag("game-automation-effective-mode"),
            )
            Text(
                strings.text("game_automation_requested", strings.text(desiredMode.labelKey)),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                strings.text("game_automation_outcome_unknown"),
                modifier = Modifier.testTag("game-automation-outcome"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                strings.text("game_automation_no_executor"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (preview.reasons.isNotEmpty()) {
                Column(
                    Modifier.fillMaxWidth().testTag("game-automation-blockers"),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(strings.text("game_automation_blocked"), style = MaterialTheme.typography.labelLarge)
                    preview.reasons.forEach { reason ->
                        Text(
                            "• ${strings.text(reason.stringKey)}",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            SecondaryButton(
                strings.text("game_automation_enable"),
                onEnable,
                Modifier.fillMaxWidth().testTag("game-automation-enable"),
                enabled = preview.canEnable,
            )
            if (stopLatched) {
                Text(
                    strings.text("game_automation_stop_latched"),
                    modifier = Modifier.testTag("game-automation-stop-latched"),
                    color = MaterialTheme.colorScheme.error,
                )
                if (!canResetStop) {
                    Text(
                        strings.text("game_automation_reset_requires_new_capture"),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                SecondaryButton(
                    strings.text("game_automation_reset_stop"),
                    onResetStop,
                    Modifier.fillMaxWidth().testTag("game-automation-reset-stop"),
                    enabled = canResetStop,
                )
            }
        }
    }
}
