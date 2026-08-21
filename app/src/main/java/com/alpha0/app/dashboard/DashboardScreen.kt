package com.alpha0.app.dashboard

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun DashboardScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    onDeviceClick: () -> Unit,
    onGameClick: (String) -> Unit
) {
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var entitlements by remember { mutableStateOf<List<DashboardApi.Entitlement>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(deviceId, accessToken) {
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
                CircularProgressIndicator()
                Text("Loading SENTINEL status…")
            }
            return@Surface
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Text("DASHBOARD", style = MaterialTheme.typography.headlineMedium)
                Text("Device security and game access", style = MaterialTheme.typography.bodyLarge)
            }
            if (error != null) {
                item { Text("Load failed: $error", color = MaterialTheme.colorScheme.error) }
            }
            device?.let { current ->
                item {
                    Card(modifier = Modifier.fillMaxWidth().clickable { onDeviceClick() }) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("DEVICE", style = MaterialTheme.typography.labelLarge)
                            Text("${current.state} · ${current.securityStatus}", style = MaterialTheme.typography.titleMedium)
                            Text(current.fingerprint, style = MaterialTheme.typography.bodySmall)
                            Text("Bound: ${current.boundAt ?: "not reported"}")
                        }
                    }
                }
            }
            item { Text("GAME ACCESS", style = MaterialTheme.typography.titleLarge) }
            if (entitlements.isEmpty()) {
                item { Text("No entitlements are currently assigned to this account.") }
            } else {
                items(entitlements, key = { it.id }) { entitlement ->
                    Card(modifier = Modifier.fillMaxWidth().clickable { onGameClick(entitlement.id) }) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(entitlement.gameName, style = MaterialTheme.typography.titleMedium)
                            Text("${entitlement.status} · ${entitlement.platform}")
                            Text("Valid until: ${entitlement.validUntil}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}
