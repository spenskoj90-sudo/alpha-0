package com.alpha0.app.quality

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.assertiveStatusSemantics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private data class QualityCategory(val id: String, val labelKey: String)

private val QUALITY_CATEGORIES = listOf(
    QualityCategory("FUNCTIONALITY", "category_functionality"),
    QualityCategory("DESIGN", "category_design"),
    QualityCategory("GAME_INTEGRATION", "category_game"),
    QualityCategory("PERFORMANCE", "category_performance"),
    QualityCategory("ACCESSIBILITY", "category_accessibility"),
    QualityCategory("VOICE_AUDIO", "category_voice"),
    QualityCategory("SECURITY_PRIVACY", "category_security"),
    QualityCategory("OTHER", "category_other"),
)

@Composable
fun QualityReportScreen(
    accessToken: String,
    api: QualityReportApi,
    diagnostics: DiagnosticLogger,
    onBack: () -> Unit,
) {
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snapshot = remember { diagnostics.createTicketSnapshot() }
    var category by remember { mutableStateOf(QUALITY_CATEGORIES.first()) }
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var attachDiagnostics by remember { mutableStateOf(snapshot.eventCount > 0) }
    var qualityProgramOptIn by remember { mutableStateOf(false) }
    var submitting by remember { mutableStateOf(false) }
    var submitted by remember { mutableStateOf<QualityReportApi.SubmittedReport?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        diagnostics.info(
            "QUALITY",
            "REPORT_UI_OPEN",
            details = mapOf(
                "snapshot_events" to snapshot.eventCount,
                "snapshot_bytes" to snapshot.encodedBytes,
                "diagnostics_mode" to diagnostics.mode(),
            )
        )
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Text(strings.text("report_problem"), style = MaterialTheme.typography.headlineMedium)
                Text(
                    strings.text("report_intro"),
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            item { Text(strings.text("category"), style = MaterialTheme.typography.titleMedium) }
            items(QUALITY_CATEGORIES, key = { it.id }) { option ->
                FilterChip(
                    selected = category.id == option.id,
                    onClick = {
                        category = option
                        diagnostics.debug("QUALITY", "CATEGORY_SELECTED", details = mapOf("category" to option.id))
                    },
                    label = { Text(strings.text(option.labelKey)) },
                )
            }

            item {
                OutlinedTextField(
                    value = title,
                    onValueChange = { if (it.length <= 160) title = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(strings.text("short_summary")) },
                    supportingText = { Text(strings.text("no_secrets")) },
                    singleLine = true,
                    enabled = !submitting && submitted == null,
                )
            }

            item {
                OutlinedTextField(
                    value = description,
                    onValueChange = { if (it.length <= 4000) description = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(strings.text("what_happened")) },
                    supportingText = { Text(strings.text("what_happened_hint")) },
                    minLines = 5,
                    enabled = !submitting && submitted == null,
                )
            }

            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text("diagnostic_snapshot"), style = MaterialTheme.typography.titleMedium)
                        Text(
                            strings.text("diagnostic_stats", snapshot.eventCount, snapshot.encodedBytes / 1024, diagnostics.mode()),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            strings.text("diagnostic_contents"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            strings.text("diagnostic_retention"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .toggleable(
                                    value = attachDiagnostics,
                                    enabled = snapshot.eventCount > 0 && !submitting && submitted == null,
                                    role = Role.Checkbox,
                                    onValueChange = { attachDiagnostics = it },
                                )
                                .padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Checkbox(
                                checked = attachDiagnostics,
                                onCheckedChange = null,
                                enabled = snapshot.eventCount > 0 && !submitting && submitted == null,
                            )
                            Text(strings.text("attach_diagnostics"))
                        }
                    }
                }
            }

            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text("quality_program"), style = MaterialTheme.typography.titleMedium)
                        Text(
                            strings.text("quality_program_body"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .toggleable(
                                    value = qualityProgramOptIn,
                                    enabled = !submitting && submitted == null,
                                    role = Role.Checkbox,
                                    onValueChange = { qualityProgramOptIn = it },
                                )
                                .padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Checkbox(
                                checked = qualityProgramOptIn,
                                onCheckedChange = null,
                                enabled = !submitting && submitted == null,
                            )
                            Text(strings.text("quality_program_opt_in"))
                        }
                    }
                }
            }

            if (diagnostics.isForensicTest()) {
                item {
                    SentinelCard {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(strings.text("physical_forensics"), style = MaterialTheme.typography.titleMedium)
                            Text(
                                strings.text("physical_forensics_body"),
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Button(onClick = {
                                diagnostics.info("QUALITY", "FORENSIC_EXPORT_REQUESTED")
                                diagnostics.exportShare(context)
                            }) {
                                Text(strings.text("export_full_log"))
                            }
                        }
                    }
                }
            }

            error?.let { code ->
                item {
                    Text(
                        strings.text("report_submit_failed", code),
                        modifier = Modifier.assertiveStatusSemantics(),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }

            submitted?.let { report ->
                item {
                    SentinelCard {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(strings.text("report_received"), style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.tertiary)
                            Text(strings.text("reference", report.id))
                            Text(strings.text("status", report.status))
                            report.problemGroupId?.let { Text(strings.text("problem_group", it), color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            report.inferredSeverity?.let { Text(strings.text("initial_severity", it), color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            report.relatedReportCount?.takeIf { it > 1 }?.let {
                                Text(strings.text("related_reports", it), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            if (report.diagnosticsRetained) {
                                Text(
                                    strings.text("diagnostics_attached", report.diagnosticsExpiresAt?.let { strings.text("expires", it) } ?: ""),
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            } else {
                                Text(strings.text("no_diagnostics_attached"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }

            item {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(
                        enabled = !submitting && submitted == null && title.trim().length >= 5 && description.isNotBlank(),
                        onClick = {
                            error = null
                            submitting = true
                            scope.launch {
                                val result = withContext(Dispatchers.IO) {
                                    api.submit(
                                        accessToken = accessToken,
                                        category = category.id,
                                        title = title,
                                        description = description,
                                        diagnosticsConsent = attachDiagnostics,
                                        qualityProgramOptIn = qualityProgramOptIn,
                                        snapshot = snapshot.takeIf { attachDiagnostics },
                                    )
                                }
                                when (result) {
                                    is QualityReportApi.SubmitResult.Success -> submitted = result.value
                                    is QualityReportApi.SubmitResult.Failure -> error = result.code
                                }
                                submitting = false
                            }
                        },
                    ) {
                        Text(strings.text(if (submitting) "sending" else "submit_report"))
                    }
                    Button(onClick = onBack, enabled = !submitting) {
                        Text(strings.text(if (submitted == null) "cancel" else "back"))
                    }
                }
            }
        }
    }
}
