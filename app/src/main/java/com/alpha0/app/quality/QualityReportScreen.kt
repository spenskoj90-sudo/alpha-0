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
import com.alpha0.app.ui.SentinelColors
import com.alpha0.app.ui.assertiveStatusSemantics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private data class QualityCategory(val id: String, val label: String)

private val QUALITY_CATEGORIES = listOf(
    QualityCategory("FUNCTIONALITY", "Functionality"),
    QualityCategory("DESIGN", "Design / visual"),
    QualityCategory("GAME_INTEGRATION", "Game integration"),
    QualityCategory("PERFORMANCE", "Performance"),
    QualityCategory("ACCESSIBILITY", "Accessibility"),
    QualityCategory("VOICE_AUDIO", "Voice / audio"),
    QualityCategory("SECURITY_PRIVACY", "Security / privacy"),
    QualityCategory("OTHER", "Other"),
)

@Composable
fun QualityReportScreen(
    accessToken: String,
    api: QualityReportApi,
    diagnostics: DiagnosticLogger,
    onBack: () -> Unit,
) {
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

    Surface(modifier = Modifier.fillMaxSize(), color = SentinelColors.Background) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Text("REPORT A PROBLEM", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "Help improve SENTINEL with a reproducible report. Diagnostic data stays on this device until you submit this form.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = SentinelColors.TextSecondary,
                )
            }

            item { Text("CATEGORY", style = MaterialTheme.typography.titleMedium) }
            items(QUALITY_CATEGORIES, key = { it.id }) { option ->
                FilterChip(
                    selected = category.id == option.id,
                    onClick = {
                        category = option
                        diagnostics.debug("QUALITY", "CATEGORY_SELECTED", details = mapOf("category" to option.id))
                    },
                    label = { Text(option.label) },
                )
            }

            item {
                OutlinedTextField(
                    value = title,
                    onValueChange = { if (it.length <= 160) title = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Short summary") },
                    supportingText = { Text("Do not include passwords, tokens or private credentials.") },
                    singleLine = true,
                    enabled = !submitting && submitted == null,
                )
            }

            item {
                OutlinedTextField(
                    value = description,
                    onValueChange = { if (it.length <= 4000) description = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("What happened?") },
                    supportingText = { Text("Describe what you expected and what actually happened. This text is never copied into diagnostic logs.") },
                    minLines = 5,
                    enabled = !submitting && submitted == null,
                )
            }

            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("DIAGNOSTIC SNAPSHOT", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "${snapshot.eventCount} structured events · ${snapshot.encodedBytes / 1024} KiB · ${diagnostics.mode()}",
                            color = SentinelColors.TextSecondary,
                        )
                        Text(
                            "Contains app lifecycle, screen-route identifiers, safe UI actions, API result/timing metadata, device/runtime state and sanitized errors. It does not contain screenshots, raw audio, passwords/tokens, request bodies, game chat or SavedVariables.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = SentinelColors.TextSecondary,
                        )
                        Text(
                            "If sent, diagnostic payloads are retained for up to 30 days; the ticket itself can remain for support history.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = SentinelColors.TextSecondary,
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
                            Text("Attach this diagnostic snapshot to my report")
                        }
                    }
                }
            }

            item {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("QUALITY IMPROVEMENT PROGRAM", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "Optional. Allow this report and its attached sanitized diagnostics to be used beyond direct support triage to improve reliability, design, accessibility and game integration quality.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = SentinelColors.TextSecondary,
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
                            Text("Contribute this report to SENTINEL quality improvement")
                        }
                    }
                }
            }

            if (diagnostics.isForensicTest()) {
                item {
                    SentinelCard {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("PHYSICAL TEST FORENSICS", style = MaterialTheme.typography.titleMedium)
                            Text(
                                "This isolated physical-test build keeps a larger local trace. Export the complete compressed trace when we need evidence beyond the bounded ticket snapshot.",
                                color = SentinelColors.TextSecondary,
                            )
                            Button(onClick = {
                                diagnostics.info("QUALITY", "FORENSIC_EXPORT_REQUESTED")
                                diagnostics.exportShare(context)
                            }) {
                                Text("Export full forensic log")
                            }
                        }
                    }
                }
            }

            error?.let { code ->
                item {
                    Text(
                        "Report could not be submitted: $code",
                        modifier = Modifier.assertiveStatusSemantics(),
                        color = SentinelColors.Danger,
                    )
                }
            }

            submitted?.let { report ->
                item {
                    SentinelCard {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("REPORT RECEIVED", style = MaterialTheme.typography.titleLarge, color = SentinelColors.Success)
                            Text("Reference: ${report.id}")
                            Text("Status: ${report.status}")
                            if (report.diagnosticsRetained) {
                                Text(
                                    "Diagnostics attached${report.diagnosticsExpiresAt?.let { " · expires $it" } ?: ""}",
                                    color = SentinelColors.TextSecondary,
                                )
                            } else {
                                Text("No diagnostics were attached.", color = SentinelColors.TextSecondary)
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
                        Text(if (submitting) "Sending…" else "Submit report")
                    }
                    Button(onClick = onBack, enabled = !submitting) {
                        Text(if (submitted == null) "Cancel" else "Back")
                    }
                }
            }
        }
    }
}
