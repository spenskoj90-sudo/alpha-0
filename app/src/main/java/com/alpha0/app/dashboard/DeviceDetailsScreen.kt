package com.alpha0.app.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
fun DeviceDetailsScreen(accessToken: String, deviceId: String, api: DashboardApi) {
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(deviceId, accessToken) {
        when (val result = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }) {
            is DashboardApi.Result.Success -> device = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
        loading = false
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("DEVICE DETAILS", style = MaterialTheme.typography.headlineMedium)
            when {
                loading -> CircularProgressIndicator()
                error != null -> Text("Load failed: $error", color = MaterialTheme.colorScheme.error)
                device != null -> {
                    val current = device!!
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("State: ${current.state}")
                            Text("Security: ${current.securityStatus}")
                            Text("Platform: ${current.platform}")
                            Text("Algorithm: ${current.algorithm}")
                            Text("Fingerprint: ${current.fingerprint}")
                            Text("Bound at: ${current.boundAt ?: "not reported"}")
                            Text("Last seen: ${current.lastSeenAt ?: "not reported"}")
                        }
                    }
                    Text("Device revoke/rotate is available in the backend, but is intentionally not exposed in this MVP screen.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
