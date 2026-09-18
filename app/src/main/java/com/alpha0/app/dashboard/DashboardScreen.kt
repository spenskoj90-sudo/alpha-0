package com.alpha0.app.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelColors
import com.alpha0.app.ui.StatusBadge
import com.alpha0.app.ui.assertiveStatusSemantics
import com.alpha0.app.ui.buttonCardSemantics
import com.alpha0.app.ui.progressStatusSemantics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun DashboardScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    onDeviceClick: () -> Unit,
    onGameClick: (String) -> Unit,
    onReportProblem: () -> Unit,
    onSignedOut: () -> Unit,
) {
    val strings = LocalAppStrings.current
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var entitlements by remember { mutableStateOf<List<DashboardApi.Entitlement>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var signingOut by remember { mutableStateOf(false) }
    var reloadGeneration by remember { mutableStateOf(0) }

    LaunchedEffect(deviceId, accessToken, reloadGeneration) {
        loading = true
        error = null
        val deviceResult = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }
        val entitlementResult = withContext(Dispatchers.IO) { api.getEntitlements(accessToken) }
        when (deviceResult) {
            is DashboardApi.Result.Success -> device = deviceResult.value
            is DashboardApi.Result.Failure -> error = deviceResult.message
        }
        when (entitlementResult) {
            is DashboardApi.Result.Success -> entitlements = entitlementResult.value
            is DashboardApi.Result.Failure -> error = error ?: entitlementResult.message
        }
        loading = false
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        if (loading) {
            Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                CircularProgressIndicator(
                    modifier = Modifier.progressStatusSemantics("Loading SENTINEL status"),
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(strings.text("loading_status"), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Surface
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Text(strings.text("dashboard"), style = MaterialTheme.typography.headlineMedium)
                Text(strings.text("dashboard_subtitle"), style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (error != null) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            strings.text("load_failed", error),
                            modifier = Modifier.assertiveStatusSemantics(),
                            color = MaterialTheme.colorScheme.error,
                        )
                        PrimaryButton(
                            text = strings.text("retry"),
                            onClick = { reloadGeneration += 1 },
                        )
                    }
                }
            }
            device?.let { current ->
                item {
                    SentinelCard(
                        modifier = Modifier
                            .buttonCardSemantics("Open device security details")
                            .clickable { onDeviceClick() },
                        scan = true,
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(strings.text("device"), style = MaterialTheme.typography.labelLarge)
                            StatusBadge(current.state, active = current.state.equals("ACTIVE", ignoreCase = true))
                            Text(current.securityStatus, style = MaterialTheme.typography.titleMedium)
                            DataText(current.fingerprint)
                            DataText(strings.text("bound", current.boundAt ?: strings.text("not_available")))
                        }
                    }
                }
            }
            item {
                SentinelCard(
                    modifier = Modifier
                        .buttonCardSemantics("Report a problem and optionally attach diagnostics")
                        .clickable { onReportProblem() },
                    scan = true,
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text("quality_feedback"), style = MaterialTheme.typography.labelLarge)
                        Text(strings.text("report_problem"), style = MaterialTheme.typography.titleMedium)
                        Text(
                            strings.text("report_problem_description"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            item {
                OutlinedButton(
                    onClick = {
                        signingOut = true
                        error = null
                    },
                    enabled = !signingOut,
                ) {
                    Text(strings.text(if (signingOut) "signing_out" else "sign_out"))
                }
                if (signingOut) {
                    LaunchedEffect(accessToken) {
                        when (val result = withContext(Dispatchers.IO) { api.revokeSession(accessToken) }) {
                            is DashboardApi.Result.Success -> {
                                signingOut = false
                                if (result.value) onSignedOut() else error = "SESSION_REVOKE_REJECTED"
                            }
                            is DashboardApi.Result.Failure -> {
                                signingOut = false
                                error = result.message
                            }
                        }
                    }
                }
            }
            item { Text(strings.text("game_access"), style = MaterialTheme.typography.titleLarge) }
            if (entitlements.isEmpty()) {
                item { Text(strings.text("no_entitlements"), color = MaterialTheme.colorScheme.onSurfaceVariant) }
            } else {
                items(entitlements, key = { it.id }) { entitlement ->
                    SentinelCard(
                        modifier = Modifier
                            .buttonCardSemantics("Open ${entitlement.gameName} access details")
                            .clickable { onGameClick(entitlement.id) }
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(entitlement.gameName, style = MaterialTheme.typography.titleMedium)
                            StatusBadge(entitlement.status, active = entitlement.status.equals("ACTIVE", ignoreCase = true))
                            Text(entitlement.platform, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            DataText(strings.text("valid_until", entitlement.validUntil))
                        }
                    }
                }
            }
        }
    }
}
