package com.alpha0.app.device

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
            Text("Bind this phone to your authenticated SENTINEL account.", style = MaterialTheme.typography.bodyLarge)

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DEVICE IDENTITY", style = MaterialTheme.typography.labelLarge)
                    Text(identity.fingerprint, style = MaterialTheme.typography.bodyMedium)
                    Text(identity.algorithm, style = MaterialTheme.typography.bodySmall)
                }
            }

            if (error != null) {
                Text("Binding failed: $error", color = MaterialTheme.colorScheme.error)
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
                modifier = Modifier.fillMaxWidth()
            ) {
                if (busy) {
                    CircularProgressIndicator()
                } else {
                    Text("Привязать устройство")
                }
            }
        }
    }
}
