package com.alpha0.app.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.DangerButton
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelColors
import com.alpha0.app.ui.StatusBadge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun DeviceDetailsScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    onRevoked: () -> Unit = {},
    onRotated: (DashboardApi.DeviceActionResult) -> Unit = {},
) {
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

    Surface(modifier = Modifier.fillMaxSize(), color = SentinelColors.Background) {
        Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("DEVICE DETAILS", style = MaterialTheme.typography.headlineMedium)
            when {
                device == null && error == null -> CircularProgressIndicator(color = SentinelColors.Primary)
                error != null -> Text("Load failed: $error", color = SentinelColors.Danger)
                else -> {
                    val current = device!!
                    SentinelCard(scan = true) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("STATE / SECURITY", style = MaterialTheme.typography.labelLarge)
                            StatusBadge(if (revoked) "REVOKED" else current.state, active = !revoked && current.state.equals("ACTIVE", true))
                            StatusBadge(if (revoked) "AT_RISK" else current.securityStatus, active = !revoked && current.securityStatus.equals("OK", true))
                            Text("Platform: ${current.platform}", style = MaterialTheme.typography.bodyMedium)
                            Text("Algorithm: ${current.algorithm}", style = MaterialTheme.typography.bodyMedium)
                            DataText("Fingerprint: ${current.fingerprint}")
                            DataText("Bound at: ${current.boundAt ?: "not reported"}")
                            DataText("Last seen: ${current.lastSeenAt ?: "not reported"}")
                        }
                    }

                    actionMessage?.let { Text(it, color = SentinelColors.Signal) }
                    error?.let { Text(it, color = SentinelColors.Danger) }

                    if (!revoked) {
                        PrimaryButton(
                            text = "Rotate key",
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
                                            is DashboardApi.Result.Success -> {
                                                val rotated = result.value
                                                if (rotated.deviceId.isNullOrBlank() || rotated.sessionToken.isNullOrBlank() || rotated.refreshToken.isNullOrBlank()) {
                                                    error = "UNEXPECTED_ERROR: Invalid rotate response: missing device/session data"
                                                } else {
                                                    actionMessage = "Device binding rotated. Session renewed."
                                                    onRotated(rotated)
                                                }
                                            }
                                            is DashboardApi.Result.Failure -> error = result.message
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        )

                        DangerButton(
                            text = "Revoke device",
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
                            modifier = Modifier.fillMaxWidth(),
                        )
                    } else {
                        Text("This device is revoked. Sign in again to continue.", color = SentinelColors.Danger)
                    }
                }
            }
        }
    }
}
