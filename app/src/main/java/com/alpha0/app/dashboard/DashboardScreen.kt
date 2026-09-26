package com.alpha0.app.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
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
import com.alpha0.app.ui.GhostButton
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge
import com.alpha0.app.ui.labelKey
import com.alpha0.app.ui.assertiveStatusSemantics
import com.alpha0.app.ui.buttonCardSemantics
import com.alpha0.app.ui.progressStatusSemantics
import com.alpha0.app.ui.statusFromRaw
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
            Column(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.progressStatusSemantics(strings.text("loading_status")),
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(strings.text("loading_status"), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Surface
        }

        val current = device
        val deviceVerified = current != null && isTrustedDeviceState(current.state, current.securityStatus)
        val attentionStatus = when {
            error != null -> SentinelStatus.WARNING
            current == null -> SentinelStatus.UNKNOWN
            deviceVerified -> SentinelStatus.ACTIVE
            else -> SentinelStatus.WARNING
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item {
                Text(strings.text("security_posture"), style = MaterialTheme.typography.headlineLarge)
                Text(
                    strings.text("security_posture_subtitle"),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (error != null) {
                item {
                    SentinelCard(kind = SentinelCardKind.OPERATIONAL) {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            StatusBadge(strings.text("attention_required"), SentinelStatus.WARNING)
                            Text(
                                strings.text("load_failed", error),
                                modifier = Modifier.assertiveStatusSemantics(),
                                color = MaterialTheme.colorScheme.error,
                            )
                            PrimaryButton(strings.text("retry"), { reloadGeneration += 1 })
                        }
                    }
                }
            }

            item {
                SentinelCard(kind = SentinelCardKind.SECURITY) {
                    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        SecurityPostureRow(
                            label = strings.text("account"),
                            value = strings.text("signed_in"),
                            supporting = strings.text("verified_session"),
                            status = SentinelStatus.VERIFIED,
                        )
                        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.58f))
                        SecurityPostureRow(
                            label = strings.text("device"),
                            value = if (deviceVerified) strings.text("trusted_device") else current?.state ?: strings.text("not_available"),
                            supporting = current?.let { "${it.state} · ${it.securityStatus}" } ?: strings.text("state_unavailable"),
                            status = if (current == null) SentinelStatus.UNKNOWN else if (deviceVerified) SentinelStatus.VERIFIED else statusFromRaw(current.state),
                            modifier = Modifier
                                .buttonCardSemantics(strings.text("open_device_identity"))
                                .clickable { onDeviceClick() },
                        )
                        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.58f))
                        SecurityPostureRow(
                            label = strings.text("attention"),
                            value = if (attentionStatus == SentinelStatus.ACTIVE) strings.text("no_required_action") else strings.text("attention_required"),
                            supporting = if (attentionStatus == SentinelStatus.ACTIVE) strings.text("loaded_states_current") else strings.text("review_security_state"),
                            status = attentionStatus,
                        )
                    }
                }
            }

            item { Text(strings.text("game_access"), style = MaterialTheme.typography.headlineMedium) }
            if (entitlements.isEmpty()) {
                item {
                    SentinelCard(kind = SentinelCardKind.CONTENT) {
                        Text(strings.text("no_entitlements"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                items(entitlements, key = { it.id }) { entitlement ->
                    SentinelCard(
                        modifier = Modifier
                            .buttonCardSemantics("Open ${entitlement.gameName} access details")
                            .clickable { onGameClick(entitlement.id) },
                        kind = SentinelCardKind.CONTENT,
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(entitlement.gameName, style = MaterialTheme.typography.titleLarge)
                                StatusBadge(entitlement.status, statusFromRaw(entitlement.status))
                            }
                            Text(entitlement.platform, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            DataText(strings.text("valid_until", entitlement.validUntil))
                        }
                    }
                }
            }

            item {
                Text(strings.text("recent_activity"), style = MaterialTheme.typography.headlineMedium)
                SentinelCard(kind = SentinelCardKind.CONTENT) {
                    Text(
                        strings.text("recent_activity_limited"),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(strings.text("support"), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    GhostButton(strings.text("report_problem"), onReportProblem)
                    GhostButton(
                        text = strings.text(if (signingOut) "signing_out" else "sign_out"),
                        enabled = !signingOut,
                        onClick = { signingOut = true; error = null },
                    )
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
            }
        }
    }
}

@Composable
private fun SecurityPostureRow(
    label: String,
    value: String,
    supporting: String,
    status: SentinelStatus,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        ) {
            Text(
                value,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.titleLarge,
            )
            val strings = LocalAppStrings.current
            StatusBadge(strings.text(status.labelKey()), status)
        }
        Text(supporting, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}


internal fun isTrustedDeviceState(state: String?, securityStatus: String?): Boolean =
    state.equals("ACTIVE", ignoreCase = true) &&
        (securityStatus.equals("OK", ignoreCase = true) || securityStatus.equals("SECURE", ignoreCase = true))

