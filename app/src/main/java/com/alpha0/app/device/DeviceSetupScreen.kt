package com.alpha0.app.device

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.SentinelAmber
import com.alpha0.app.ui.SentinelBackground
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelDanger
import com.alpha0.app.ui.SentinelTextSecondary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun DeviceSetupScreen(
    accessToken: String,
    deviceIdentity: DeviceIdentity,
    api: DeviceApi,
    onBound: (String) -> Unit
) {
    val identity = remember { deviceIdentity.getIdentityInfo() }
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("DEVICE SETUP", style = MaterialTheme.typography.headlineMedium)
            Text("Bind this phone to your authenticated SENTINEL account.", style = MaterialTheme.typography.bodyLarge, color = SentinelTextSecondary)

            SentinelCard(modifier = Modifier.fillMaxWidth(), cornerMarks = true) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DEVICE IDENTITY", style = MaterialTheme.typography.labelLarge, color = SentinelAmber)
                    DataText(identity.fingerprint)
                    DataText(identity.algorithm)
                }
            }

            if (error != null) {
                Text("Binding failed: $error", color = SentinelDanger)
            }

            Button(
                onClick = {
                    if (busy) return@Button
                    busy = true
                    error = null
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            api.bind(
                                accessToken = accessToken,
                                platform = "android",
                                publicKeyDerB64 = deviceIdentity.getPublicKeyDerBase64(),
                                fingerprintSha256 = identity.fingerprint
                            )
                        }
                        busy = false
                        when (result) {
                            is DeviceApi.Result.Success -> onBound(result.value.deviceId)
                            is DeviceApi.Result.Failure -> error = result.message
                        }
                    }
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = SentinelAmber, contentColor = SentinelBackground),
            ) {
                if (busy) {
                    CircularProgressIndicator(color = SentinelBackground, strokeWidth = 2.dp)
                } else {
                    Text("Привязать устройство")
                }
            }
        }
    }
}
