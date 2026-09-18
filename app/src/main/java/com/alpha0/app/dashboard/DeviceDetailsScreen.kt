package com.alpha0.app.dashboard

import android.content.Intent
import android.net.Uri
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.FederatedAuthCoordinator
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.ui.DataText
import com.alpha0.app.ui.DangerButton
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.StatusBadge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun DeviceDetailsScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    authApi: AuthApi,
    federatedAuth: FederatedAuthCoordinator,
    federatedCallbackUri: Uri?,
    onFederatedCallbackConsumed: () -> Unit,
    deviceIdentity: DeviceIdentity,
    onRevoked: () -> Unit = {},
    onRotated: (DashboardApi.DeviceActionResult) -> Unit = {},
) {
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var accountSecurity by remember { mutableStateOf<AuthApi.AccountSecurity?>(null) }
    var providerStatuses by remember { mutableStateOf<List<AuthApi.ProviderStatus>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    var accountError by remember { mutableStateOf<String?>(null) }
    var actionInProgress by remember { mutableStateOf(false) }
    var providerActionInProgress by remember { mutableStateOf(false) }
    var actionMessage by remember { mutableStateOf<String?>(null) }
    var revoked by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    suspend fun refreshAccountSecurity() {
        when (val result = authApi.accountSecurity(accessToken)) {
            is AuthApi.AccountSecurityResult.Success -> {
                accountSecurity = result.value
                accountError = null
            }
            is AuthApi.AccountSecurityResult.Failure -> accountError = result.message
        }
        providerStatuses = when (val result = authApi.providerCatalog()) {
            is AuthApi.ProviderCatalogResult.Success -> result.providers.filter {
                it.enabled && federatedAuth.isProviderCompatible(it)
            }
            is AuthApi.ProviderCatalogResult.Failure -> emptyList()
        }
    }

    LaunchedEffect(deviceId, accessToken) {
        when (val result = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }) {
            is DashboardApi.Result.Success -> device = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
        refreshAccountSecurity()
    }

    LaunchedEffect(federatedCallbackUri, accessToken) {
        val callback = federatedCallbackUri ?: return@LaunchedEffect
        providerActionInProgress = true
        accountError = null
        val result = federatedAuth.completeBrowserLinkCallback(callback, accessToken)
        onFederatedCallbackConsumed()
        providerActionInProgress = false
        when (result) {
            is AuthApi.ActionResult.Success -> {
                actionMessage = strings.text("provider_linked")
                refreshAccountSecurity()
            }
            is AuthApi.ActionResult.Failure -> {
                accountError = when (result.message) {
                    "AUTH_PROVIDER_CANCELLED" -> strings.text("federated_cancelled")
                    "AUTH_CALLBACK_EXPIRED" -> strings.text("federated_expired")
                    "EXTERNAL_IDENTITY_ALREADY_LINKED", "PROVIDER_ALREADY_LINKED" ->
                        strings.text("provider_link_conflict")
                    else -> strings.text("federated_failed", result.message)
                }
            }
        }
    }

    fun linkGoogle() {
        providerActionInProgress = true
        accountError = null
        scope.launch {
            when (val result = federatedAuth.linkGoogle(accessToken)) {
                is AuthApi.ActionResult.Success -> {
                    actionMessage = strings.text("provider_linked")
                    refreshAccountSecurity()
                }
                is AuthApi.ActionResult.Failure -> {
                    accountError = when (result.message) {
                        "GOOGLE_CREDENTIAL_CANCELLED" -> strings.text("federated_cancelled")
                        "EXTERNAL_IDENTITY_ALREADY_LINKED", "PROVIDER_ALREADY_LINKED" ->
                            strings.text("provider_link_conflict")
                        else -> strings.text("federated_failed", result.message)
                    }
                }
            }
            providerActionInProgress = false
        }
    }

    fun linkBrowserProvider(provider: String) {
        providerActionInProgress = true
        accountError = null
        scope.launch {
            when (val result = federatedAuth.beginBrowser(provider, operation = "link")) {
                is FederatedAuthCoordinator.BrowserLaunchResult.Failure -> {
                    accountError = strings.text("federated_failed", result.message)
                    providerActionInProgress = false
                }
                is FederatedAuthCoordinator.BrowserLaunchResult.Success -> {
                    val launched = runCatching {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.value.url)))
                    }.isSuccess
                    providerActionInProgress = false
                    if (launched) {
                        actionMessage = strings.text(
                            "provider_link_return_hint",
                            if (provider == "telegram") "Telegram" else "VK",
                        )
                    } else {
                        federatedAuth.cancelPendingBrowserFlow()
                        accountError = strings.text("browser_unavailable")
                    }
                }
            }
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(strings.text("device_details"), style = MaterialTheme.typography.headlineMedium)

            SentinelCard(scan = false) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(strings.text("account_security"), style = MaterialTheme.typography.labelLarge)
                    val account = accountSecurity
                    if (account == null && accountError == null) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    } else if (account != null) {
                        DataText(strings.text("account_email", account.email ?: strings.text("not_available")))
                        StatusBadge(
                            strings.text(if (account.emailVerified) "email_verified_status" else "email_unverified_status"),
                            active = account.emailVerified,
                        )
                        Text(
                            strings.text(
                                "password_status",
                                strings.text(if (account.passwordEnabled) "enabled" else "disabled"),
                            ),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        val linked = account.providers.toSet()
                        Text(
                            strings.text(
                                "linked_providers",
                                if (linked.isEmpty()) strings.text("none") else linked.joinToString(", "),
                            ),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        val available = providerStatuses.filter { it.provider !in linked }
                        if (available.isNotEmpty()) {
                            Text(strings.text("link_provider"), style = MaterialTheme.typography.bodyMedium)
                            if (available.any { it.provider == "google" }) {
                                PrimaryButton(
                                    text = strings.text("link_google"),
                                    enabled = !providerActionInProgress,
                                    onClick = ::linkGoogle,
                                    modifier = Modifier.fillMaxWidth(),
                                )
                            }
                            if (available.any { it.provider == "telegram" }) {
                                PrimaryButton(
                                    text = strings.text("link_telegram"),
                                    enabled = !providerActionInProgress,
                                    onClick = { linkBrowserProvider("telegram") },
                                    modifier = Modifier.fillMaxWidth(),
                                )
                            }
                            if (available.any { it.provider == "vk" }) {
                                PrimaryButton(
                                    text = strings.text("link_vk"),
                                    enabled = !providerActionInProgress,
                                    onClick = { linkBrowserProvider("vk") },
                                    modifier = Modifier.fillMaxWidth(),
                                )
                            }
                            Text(
                                strings.text("provider_link_privacy"),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    accountError?.let {
                        Text(it, color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            when {
                device == null && error == null -> CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                error != null -> Text(strings.text("load_failed", error), color = MaterialTheme.colorScheme.error)
                else -> {
                    val current = device!!
                    SentinelCard(scan = true) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(strings.text("state_security"), style = MaterialTheme.typography.labelLarge)
                            StatusBadge(
                                if (revoked) strings.text("status_revoked") else current.state,
                                active = !revoked && current.state.equals("ACTIVE", true),
                            )
                            StatusBadge(
                                if (revoked) strings.text("status_at_risk") else current.securityStatus,
                                active = !revoked && current.securityStatus.equals("OK", true),
                            )
                            Text(strings.text("platform", current.platform), style = MaterialTheme.typography.bodyMedium)
                            Text(strings.text("algorithm", current.algorithm), style = MaterialTheme.typography.bodyMedium)
                            DataText(strings.text("fingerprint", current.fingerprint))
                            DataText(strings.text("bound", current.boundAt ?: strings.text("not_available")))
                            DataText(strings.text("last_seen", current.lastSeenAt ?: strings.text("not_available")))
                        }
                    }

                    actionMessage?.let { Text(it, color = MaterialTheme.colorScheme.tertiary) }

                    if (!revoked) {
                        PrimaryButton(
                            text = strings.text("rotate_key"),
                            enabled = !actionInProgress,
                            onClick = {
                                actionInProgress = true
                                error = null
                                actionMessage = null
                                scope.launch(Dispatchers.IO) {
                                    var rotated: DashboardApi.DeviceActionResult? = null
                                    var failure: String? = null
                                    var candidate: DeviceIdentity.RotationCandidate? = null
                                    try {
                                        val prepared = deviceIdentity.prepareRotation()
                                        candidate = prepared
                                        when (
                                            val result = api.rotateDevice(
                                                accessToken,
                                                current.deviceId,
                                                current.platform,
                                                prepared.publicKeyDerBase64,
                                                prepared.fingerprint,
                                            )
                                        ) {
                                            is DashboardApi.Result.Success -> {
                                                val value = result.value
                                                if (
                                                    value.deviceId.isNullOrBlank() ||
                                                    value.sessionToken.isNullOrBlank() ||
                                                    value.refreshToken.isNullOrBlank()
                                                ) {
                                                    deviceIdentity.abortRotation(prepared)
                                                    failure = "UNEXPECTED_ERROR: Invalid rotate response: missing device/session data"
                                                } else {
                                                    deviceIdentity.commitRotation(prepared)
                                                    rotated = value
                                                }
                                            }
                                            is DashboardApi.Result.Failure -> {
                                                deviceIdentity.abortRotation(prepared)
                                                failure = result.message
                                            }
                                        }
                                    } catch (exception: Exception) {
                                        candidate?.let(deviceIdentity::abortRotation)
                                        failure = "KEY_ROTATION_${exception.javaClass.simpleName}"
                                    }
                                    withContext(Dispatchers.Main) {
                                        actionInProgress = false
                                        val value = rotated
                                        if (value == null) {
                                            error = failure ?: "KEY_ROTATION_FAILED"
                                        } else {
                                            actionMessage = strings.text("rotation_success")
                                            onRotated(value)
                                        }
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        )

                        DangerButton(
                            text = strings.text("revoke_device"),
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
                                                actionMessage = strings.text("revoked")
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
                        Text(strings.text("revoked"), color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}
