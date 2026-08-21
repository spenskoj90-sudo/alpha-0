package com.alpha0.app.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.security.DeviceIdentity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun DeviceDetailsScreen(accessToken: String, deviceId: String, api: DashboardApi, onRevoked: () -> Unit = {}) {
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var actionInProgress by remember { mutableStateOf(false) }
    var actionMessage by remember { mutableStateOf<String?>(null) }
    var revoked by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val identity = remember { DeviceIdentity() }

    LaunchedEffect(deviceId, accessToken) {
        when (val result = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }) {
            is DashboardApi.Result.Success -> device = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("DEVICE DETAILS", style = MaterialTheme.typography.headlineMedium)
            when {
                device == null && error == null -> CircularProgressIndicator()
                error != null -> Text("Load failed: $error", color = MaterialTheme.colorScheme.error)
                else -> {
                    val current = device!!
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("State: ${if (revoked) "REVOKED" else current.state}")
                            Text("Security: ${if (revoked) "AT_RISK" else current.securityStatus}")
                            Text("Platform: ${current.platform}")
                            Text("Algorithm: ${current.algorithm}")
                            Text("Fingerprint: ${current.fingerprint}")
                            Text("Bound at: ${current.boundAt ?: "not reported"}")
                            Text("Last seen: ${current.lastSeenAt ?: "not reported"}")
                        }
                    }

                    actionMessage?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
                    error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

                    if (!revoked) {
                        OutlinedButton(
                            enabled = !actionInProgress,
                            onClick = {
                                actionInProgress = true
                                error = null
                                actionMessage = null
                                scope.launch(Dispatchers.IO) {
                                    val info = identity.getIdentityInfo()
                                    val publicKey = identity.getPublicKeyDerBase64()
                                    val result = api.rotateDevice(accessToken, current.deviceId, current.platform, publicKey, info.fingerprint)
                                    withContext(Dispatchers.Main) {
                                        actionInProgress = false
                                        when (result) {
                                            is DashboardApi.Result.Success -> actionMessage = "Device binding rotated. New device id: ${result.value.deviceId}"
                                            is DashboardApi.Result.Failure -> error = result.message
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Rotate key")
                        }

                        Button(
                            enabled = !actionInProgress,
                            onClick = {
                                actionInProgress = true
                                error = null
                                actionMessage = null
                                scope.launch(Dispatchers.IO) {
                                    val result = api.revokeDevice(accessToken, current.deviceId)
                                    withContext(Dispatchers.Main) {
                                        actionInProgress = false
                                        when (result) {
                                            is DashboardApi.Result.Success -> {
                                                revoked = true
                                                actionMessage = "Device revoked. Sign in again to continue."
                                                onRevoked()
                                            }
                                            is DashboardApi.Result.Failure -> error = result.message
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Revoke device")
                        }
                    } else {
                        Text("This device is revoked. Sign in again to continue.", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
