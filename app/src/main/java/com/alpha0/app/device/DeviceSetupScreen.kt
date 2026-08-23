package com.alpha0.app.device

import android.content.Intent
import android.net.Uri
import android.provider.Settings
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelColors
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
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val identity = remember { deviceIdentity.getIdentityInfo() }
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var batteryOptimizationIgnored by remember { mutableStateOf(BatteryOptimization.isIgnored(context)) }

    DisposableEffect(lifecycleOwner, context) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                batteryOptimizationIgnored = BatteryOptimization.isIgnored(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = SentinelColors.Background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("DEVICE SETUP", style = MaterialTheme.typography.headlineMedium)
            Text("Bind this phone to your authenticated SENTINEL account.", style = MaterialTheme.typography.bodyLarge, color = SentinelColors.TextSecondary)

            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DEVICE IDENTITY", style = MaterialTheme.typography.labelLarge, color = SentinelColors.TextPrimary)
                    DataText(identity.fingerprint)
                    DataText(identity.algorithm)
                }
            }

            if (!batteryOptimizationIgnored) {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("BACKGROUND NETWORK", style = MaterialTheme.typography.labelLarge, color = SentinelColors.TextPrimary)
                        Text(
                            "Some Android devices restrict background network activity. Allowing SENTINEL to ignore battery optimization helps prevent delayed first requests and session timeouts.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = SentinelColors.TextSecondary
                        )
                        PrimaryButton(
                            text = "Allow background operation",
                            onClick = {
                                val opened = BatteryOptimization.request(context)
                                if (!opened) {
                                    runCatching {
                                        context.startActivity(
                                            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                                data = Uri.parse("package:${context.packageName}")
                                            }
                                        )
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            if (error != null) {
                Text("Binding failed: $error", color = SentinelColors.Danger, style = MaterialTheme.typography.bodyMedium)
            }

            PrimaryButton(
                text = "Привязать устройство",
                onClick = {
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
                if (busy) CircularProgressIndicator() else Text("Привязать устройство")
            }
        }
    }
}
