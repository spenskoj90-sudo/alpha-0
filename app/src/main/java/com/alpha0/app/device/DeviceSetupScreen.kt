package com.alpha0.app.device

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.LocalAppStrings
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
    onBound: (DeviceApi.ProvenSession) -> Unit
) {
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val identity = remember { deviceIdentity.getIdentityInfo() }
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingBind by remember { mutableStateOf<DeviceApi.BindResult?>(null) }
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

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(strings.text("device_setup"), style = MaterialTheme.typography.headlineMedium)
            Text(
                strings.text("device_setup_intro"),
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            SentinelCard {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(strings.text("step_identity"), style = MaterialTheme.typography.labelLarge)
                    Text(strings.text("identity_ready"), style = MaterialTheme.typography.titleMedium)
                    DataText(identity.fingerprint)
                    DataText(identity.algorithm)
                    Text(strings.text("setup_privacy"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            if (!batteryOptimizationIgnored) {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text("step_background"), style = MaterialTheme.typography.labelLarge)
                        Text(
                            strings.text("background_explanation"),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        PrimaryButton(
                            text = strings.text("allow_background"),
                            onClick = {
                                val opened = BatteryOptimization.openSettings(context)
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

            if (batteryOptimizationIgnored) {
                SentinelCard {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(strings.text("step_background"), style = MaterialTheme.typography.labelLarge)
                        Text(strings.text("background_allowed"), color = MaterialTheme.colorScheme.tertiary)
                    }
                }
            }

            if (error != null) {
                Text(strings.text("setup_failed", error), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
            }

            Text(strings.text("step_proof"), style = MaterialTheme.typography.labelLarge)

            PrimaryButton(
                text = strings.text(if (pendingBind == null) "bind_device" else "retry_proof"),
                onClick = {
                    busy = true
                    error = null
                    scope.launch {
                        val existingBinding = pendingBind
                        val bound = if (existingBinding == null) {
                            when (val bind = withContext(Dispatchers.IO) {
                                api.bind(
                                    accessToken = accessToken,
                                    platform = "android",
                                    publicKeyDerB64 = deviceIdentity.getPublicKeyDerBase64(),
                                    fingerprintSha256 = identity.fingerprint
                                )
                            }) {
                                is DeviceApi.Result.Success -> {
                                    pendingBind = bind.value
                                    bind.value
                                }
                                is DeviceApi.Result.Failure -> {
                                    busy = false
                                    error = bind.message
                                    return@launch
                                }
                            }
                        } else {
                            when (val renewed = withContext(Dispatchers.IO) {
                                api.challenge(accessToken, existingBinding.deviceId)
                            }) {
                                is DeviceApi.ChallengeResult.Success -> {
                                    existingBinding.copy(challenge = renewed.challenge).also { pendingBind = it }
                                }
                                is DeviceApi.ChallengeResult.Failure -> {
                                    busy = false
                                    error = "CHALLENGE_RENEWAL_${renewed.message}"
                                    return@launch
                                }
                            }
                        }

                        when (val proof = withContext(Dispatchers.IO) {
                            api.prove(bound.deviceId, bound.challenge, deviceIdentity)
                        }) {
                            is DeviceApi.ProofResult.Success -> {
                                pendingBind = null
                                busy = false
                                onBound(proof.value)
                            }
                            is DeviceApi.ProofResult.Failure -> {
                                // Keep the bound device. The next retry obtains a fresh one-time
                                // challenge before signing, so a transient failure cannot create
                                // an unnecessary second device registration.
                                pendingBind = bound
                                busy = false
                                error = proof.message
                            }
                        }
                    }
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (busy) {
                    Column { CircularProgressIndicator(); Text(strings.text("setup_busy")) }
                } else {
                    Text(strings.text(if (pendingBind == null) "bind_device" else "retry_proof"))
                }
            }
        }
    }
}
