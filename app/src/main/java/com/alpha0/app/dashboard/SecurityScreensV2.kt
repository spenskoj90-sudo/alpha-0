package com.alpha0.app.dashboard

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.SentinelCard
import com.alpha0.app.ui.SentinelCardKind
import com.alpha0.app.ui.SentinelStatus
import com.alpha0.app.ui.StatusBadge
import com.alpha0.app.ui.statusFromRaw
import com.alpha0.app.ui.labelKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class SecurityDetailSection {
    ACCOUNT,
    MFA,
    RECOVERY,
    SESSIONS,
    DEVICE,
    PROVIDERS,
}

@Composable
fun SecurityHubScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    authApi: AuthApi,
    onSection: (SecurityDetailSection) -> Unit,
) {
    val strings = LocalAppStrings.current
    var account by remember { mutableStateOf<AuthApi.AccountSecurity?>(null) }
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var accountFailed by remember { mutableStateOf(false) }
    var deviceFailed by remember { mutableStateOf(false) }

    LaunchedEffect(accessToken, deviceId) {
        when (val result = authApi.accountSecurity(accessToken)) {
            is AuthApi.AccountSecurityResult.Success -> account = result.value
            is AuthApi.AccountSecurityResult.Failure -> accountFailed = true
        }
        when (val result = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }) {
            is DashboardApi.Result.Success -> device = result.value
            is DashboardApi.Result.Failure -> deviceFailed = true
        }
    }

    val accountState = when {
        accountFailed -> SentinelStatus.UNAVAILABLE
        account == null -> SentinelStatus.PENDING
        account!!.emailVerified -> SentinelStatus.VERIFIED
        else -> SentinelStatus.WARNING
    }
    val mfaState = when {
        accountFailed -> SentinelStatus.UNAVAILABLE
        account == null -> SentinelStatus.PENDING
        account!!.mfaEnabled -> SentinelStatus.VERIFIED
        else -> SentinelStatus.WARNING
    }
    val recoveryState = when {
        accountFailed -> SentinelStatus.UNAVAILABLE
        account == null -> SentinelStatus.PENDING
        !account!!.mfaEnabled -> SentinelStatus.UNAVAILABLE
        account!!.mfaRecoveryCodesRemaining > 0 -> SentinelStatus.WARNING
        else -> SentinelStatus.WARNING
    }
    val deviceState = when {
        deviceFailed -> SentinelStatus.UNAVAILABLE
        device == null -> SentinelStatus.PENDING
        device!!.state.equals("ACTIVE", true) && device!!.securityStatus.equals("OK", true) -> SentinelStatus.VERIFIED
        else -> statusFromRaw(device!!.state)
    }
    val providerState = when {
        accountFailed -> SentinelStatus.UNAVAILABLE
        account == null -> SentinelStatus.PENDING
        account!!.providers.isNotEmpty() -> SentinelStatus.VERIFIED
        else -> SentinelStatus.UNKNOWN
    }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(strings.text("security"), style = MaterialTheme.typography.headlineLarge)
            Text(strings.text("security_subtitle"), color = MaterialTheme.colorScheme.onSurfaceVariant)

            SecurityHubRow(
                strings.text("account_security"),
                account?.let { if (it.emailVerified) strings.text("email_verified_status") else strings.text("email_unverified_status") }
                    ?: strings.text("loading"),
                accountState,
            ) { onSection(SecurityDetailSection.ACCOUNT) }

            SecurityHubRow(
                strings.text("mfa_full"),
                account?.let { strings.text(if (it.mfaEnabled) "enabled" else "disabled") } ?: strings.text("loading"),
                mfaState,
            ) { onSection(SecurityDetailSection.MFA) }

            SecurityHubRow(
                strings.text("recovery"),
                account?.let {
                    if (it.mfaEnabled) strings.text("mfa_recovery_remaining", it.mfaRecoveryCodesRemaining)
                    else strings.text("state_unavailable")
                } ?: strings.text("loading"),
                recoveryState,
            ) { onSection(SecurityDetailSection.RECOVERY) }

            SecurityHubRow(
                strings.text("sessions"),
                strings.text("sessions_current_only"),
                SentinelStatus.ACTIVE,
            ) { onSection(SecurityDetailSection.SESSIONS) }

            SecurityHubRow(
                strings.text("device_identity"),
                device?.let { "${it.state} · ${it.securityStatus}" } ?: strings.text("loading"),
                deviceState,
            ) { onSection(SecurityDetailSection.DEVICE) }

            SecurityHubRow(
                strings.text("linked_providers_title"),
                account?.let {
                    if (it.providers.isEmpty()) strings.text("none") else it.providers.joinToString(", ")
                } ?: strings.text("loading"),
                providerState,
            ) { onSection(SecurityDetailSection.PROVIDERS) }

            Text(
                strings.text("dangerous_actions_scope"),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun SecurityHubRow(
    title: String,
    supporting: String,
    status: SentinelStatus,
    onClick: () -> Unit,
) {
    SentinelCard(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        kind = SentinelCardKind.SECURITY,
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(title, style = MaterialTheme.typography.titleLarge)
                Text("›", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            val strings = LocalAppStrings.current
            StatusBadge(strings.text(status.labelKey()), status)
            Text(supporting, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
fun AccountSecurityDetailScreen(
    section: SecurityDetailSection,
    accessToken: String,
    authApi: AuthApi,
    federatedAuth: FederatedAuthCoordinator,
    federatedCallbackUri: Uri?,
    onFederatedCallbackConsumed: () -> Unit,
    onMfaEnabled: (List<String>) -> Unit,
    onSessionBoundary: () -> Unit,
) {
    require(section in setOf(SecurityDetailSection.ACCOUNT, SecurityDetailSection.MFA, SecurityDetailSection.RECOVERY, SecurityDetailSection.PROVIDERS))
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var account by remember { mutableStateOf<AuthApi.AccountSecurity?>(null) }
    var providers by remember { mutableStateOf<List<AuthApi.ProviderStatus>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var enrollment by remember { mutableStateOf<AuthApi.TotpEnrollment?>(null) }
    var code by remember { mutableStateOf("") }

    suspend fun refresh() {
        when (val result = authApi.accountSecurity(accessToken)) {
            is AuthApi.AccountSecurityResult.Success -> {
                account = result.value
                error = null
            }
            is AuthApi.AccountSecurityResult.Failure -> error = result.message
        }
        providers = when (val result = authApi.providerCatalog()) {
            is AuthApi.ProviderCatalogResult.Success -> result.providers.filter { it.enabled && federatedAuth.isProviderCompatible(it) }
            is AuthApi.ProviderCatalogResult.Failure -> emptyList()
        }
    }

    LaunchedEffect(accessToken) { refresh() }

    LaunchedEffect(federatedCallbackUri, accessToken) {
        val callback = federatedCallbackUri ?: return@LaunchedEffect
        if (section != SecurityDetailSection.PROVIDERS) return@LaunchedEffect
        busy = true
        error = null
        when (val result = federatedAuth.completeBrowserLinkCallback(callback, accessToken)) {
            is AuthApi.ActionResult.Success -> {
                message = strings.text("provider_linked")
                refresh()
            }
            is AuthApi.ActionResult.Failure -> error = strings.text("federated_failed", result.message)
        }
        onFederatedCallbackConsumed()
        busy = false
    }

    fun beginMfa() {
        busy = true; error = null; message = null
        scope.launch {
            when (val result = authApi.enrollTotp(accessToken)) {
                is AuthApi.TotpEnrollmentResult.Success -> {
                    enrollment = result.value
                    code = ""
                    message = strings.text("mfa_enrollment_started")
                }
                is AuthApi.TotpEnrollmentResult.Failure -> error = strings.text("auth_failed", result.message)
            }
            busy = false
        }
    }

    fun confirmMfa() {
        if (code.trim().length < 6) { error = strings.text("mfa_code_required"); return }
        busy = true; error = null
        scope.launch {
            when (val result = authApi.confirmTotp(accessToken, code)) {
                is AuthApi.RecoveryCodesResult.Success -> onMfaEnabled(result.codes)
                is AuthApi.RecoveryCodesResult.Failure -> error = strings.text("auth_failed", result.message)
            }
            busy = false
        }
    }

    fun disableMfa() {
        if (code.trim().length < 6) { error = strings.text("mfa_code_required"); return }
        busy = true; error = null
        scope.launch {
            when (val result = authApi.disableTotp(accessToken, code)) {
                is AuthApi.ActionResult.Success -> onSessionBoundary()
                is AuthApi.ActionResult.Failure -> error = strings.text("auth_failed", result.message)
            }
            busy = false
        }
    }

    fun rotateRecovery() {
        if (code.trim().length < 6) { error = strings.text("mfa_code_required"); return }
        busy = true; error = null
        scope.launch {
            when (val result = authApi.rotateRecoveryCodes(accessToken, code)) {
                is AuthApi.RecoveryCodesResult.Success -> onMfaEnabled(result.codes)
                is AuthApi.RecoveryCodesResult.Failure -> error = strings.text("auth_failed", result.message)
            }
            busy = false
        }
    }

    fun linkGoogle() {
        busy = true; error = null
        scope.launch {
            when (val result = federatedAuth.linkGoogle(accessToken)) {
                is AuthApi.ActionResult.Success -> { message = strings.text("provider_linked"); refresh() }
                is AuthApi.ActionResult.Failure -> error = strings.text("federated_failed", result.message)
            }
            busy = false
        }
    }

    fun linkBrowser(provider: String) {
        busy = true; error = null
        scope.launch {
            when (val result = federatedAuth.beginBrowser(provider, operation = "link")) {
                is FederatedAuthCoordinator.BrowserLaunchResult.Failure -> {
                    error = strings.text("federated_failed", result.message)
                    busy = false
                }
                is FederatedAuthCoordinator.BrowserLaunchResult.Success -> {
                    val launched = runCatching {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.value.url)))
                    }.isSuccess
                    if (!launched) {
                        federatedAuth.cancelPendingBrowserFlow()
                        error = strings.text("browser_unavailable")
                    } else {
                        message = strings.text("provider_link_return_hint", if (provider == "telegram") "Telegram" else "VK")
                    }
                    busy = false
                }
            }
        }
    }

    val title = when (section) {
        SecurityDetailSection.ACCOUNT -> strings.text("account_security")
        SecurityDetailSection.MFA -> strings.text("mfa_full")
        SecurityDetailSection.RECOVERY -> strings.text("recovery")
        SecurityDetailSection.PROVIDERS -> strings.text("linked_providers_title")
        else -> strings.text("security")
    }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(title, style = MaterialTheme.typography.headlineLarge)
            if (account == null && error == null) CircularProgressIndicator()
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            message?.let { Text(it, color = MaterialTheme.colorScheme.secondary) }

            account?.let { current ->
                when (section) {
                    SecurityDetailSection.ACCOUNT -> {
                        SentinelCard(kind = SentinelCardKind.SECURITY) {
                            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                StatusBadge(
                                    strings.text(if (current.emailVerified) "email_verified_status" else "email_unverified_status"),
                                    if (current.emailVerified) SentinelStatus.VERIFIED else SentinelStatus.WARNING,
                                )
                                DataText(strings.text("account_email", current.email ?: strings.text("not_available")))
                                Text(strings.text("password_status", strings.text(if (current.passwordEnabled) "enabled" else "disabled")))
                            }
                        }
                    }

                    SecurityDetailSection.MFA -> {
                        SentinelCard(kind = SentinelCardKind.SECURITY) {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                StatusBadge(
                                    strings.text(if (current.mfaEnabled) "enabled" else "disabled"),
                                    if (current.mfaEnabled) SentinelStatus.VERIFIED else SentinelStatus.WARNING,
                                )
                                if (!current.mfaEnabled && enrollment == null) {
                                    PrimaryButton(strings.text("enable_mfa"), ::beginMfa, Modifier.fillMaxWidth(), !busy)
                                }
                                enrollment?.let { setup ->
                                    Text(strings.text("mfa_setup_instructions"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    SecondaryButton(
                                        strings.text("open_authenticator"),
                                        onClick = {
                                            if (!runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(setup.otpauthUri))) }.isSuccess) {
                                                error = strings.text("authenticator_unavailable")
                                            }
                                        },
                                        modifier = Modifier.fillMaxWidth(),
                                        enabled = !busy,
                                    )
                                    DataText(strings.text("mfa_secret", setup.secret))
                                    OutlinedTextField(
                                        value = code,
                                        onValueChange = { code = it.trim(); error = null },
                                        modifier = Modifier.fillMaxWidth(),
                                        label = { Text(strings.text("mfa_code")) },
                                        enabled = !busy,
                                        singleLine = true,
                                    )
                                    PrimaryButton(strings.text("confirm_mfa"), ::confirmMfa, Modifier.fillMaxWidth(), !busy)
                                }
                                if (current.mfaEnabled) {
                                    OutlinedTextField(
                                        value = code,
                                        onValueChange = { code = it.trim(); error = null },
                                        modifier = Modifier.fillMaxWidth(),
                                        label = { Text(strings.text("mfa_or_recovery_code")) },
                                        enabled = !busy,
                                        singleLine = true,
                                    )
                                    Text(strings.text("dangerous_actions_scope"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    DangerButton(strings.text("disable_mfa"), ::disableMfa, Modifier.fillMaxWidth(), !busy)
                                }
                            }
                        }
                    }

                    SecurityDetailSection.RECOVERY -> {
                        SentinelCard(kind = SentinelCardKind.SECURITY) {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                if (!current.mfaEnabled) {
                                    StatusBadge(strings.text("state_unavailable"), SentinelStatus.UNAVAILABLE)
                                    Text(strings.text("mfa_status", strings.text("disabled")), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                } else {
                                    StatusBadge(strings.text("recovery_codes_available"), SentinelStatus.WARNING)
                                    Text(strings.text("mfa_recovery_remaining", current.mfaRecoveryCodesRemaining))
                                    OutlinedTextField(
                                        value = code,
                                        onValueChange = { code = it.trim(); error = null },
                                        modifier = Modifier.fillMaxWidth(),
                                        label = { Text(strings.text("mfa_or_recovery_code")) },
                                        enabled = !busy,
                                        singleLine = true,
                                    )
                                    PrimaryButton(strings.text("rotate_recovery_codes"), ::rotateRecovery, Modifier.fillMaxWidth(), !busy)
                                }
                            }
                        }
                    }

                    SecurityDetailSection.PROVIDERS -> {
                        SentinelCard(kind = SentinelCardKind.SECURITY) {
                            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                val linked = current.providers.toSet()
                                StatusBadge(
                                    if (linked.isEmpty()) strings.text("none") else linked.joinToString(", "),
                                    if (linked.isEmpty()) SentinelStatus.UNKNOWN else SentinelStatus.VERIFIED,
                                )
                                Text(strings.text("provider_link_privacy"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                val available = providers.filter { it.provider !in linked }
                                if (available.any { it.provider == "google" }) SecondaryButton(strings.text("link_google"), ::linkGoogle, Modifier.fillMaxWidth(), !busy)
                                if (available.any { it.provider == "telegram" }) SecondaryButton(strings.text("link_telegram"), { linkBrowser("telegram") }, Modifier.fillMaxWidth(), !busy)
                                if (available.any { it.provider == "vk" }) SecondaryButton(strings.text("link_vk"), { linkBrowser("vk") }, Modifier.fillMaxWidth(), !busy)
                            }
                        }
                    }
                    else -> Unit
                }
            }
        }
    }
}

@Composable
fun SessionsDetailScreen() {
    val strings = LocalAppStrings.current
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text(strings.text("sessions"), style = MaterialTheme.typography.headlineLarge)
            SentinelCard(kind = SentinelCardKind.SECURITY) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatusBadge(strings.text("sessions_current_only"), SentinelStatus.ACTIVE)
                    Text(
                        strings.text("activity_limited_body"),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
fun DeviceIdentityDetailScreen(
    accessToken: String,
    deviceId: String,
    api: DashboardApi,
    deviceIdentity: DeviceIdentity,
    onRevoked: () -> Unit,
    onRotated: (DashboardApi.DeviceActionResult) -> Unit,
) {
    val strings = LocalAppStrings.current
    val scope = rememberCoroutineScope()
    var device by remember { mutableStateOf<DashboardApi.Device?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var showRevokeConfirm by remember { mutableStateOf(false) }

    LaunchedEffect(accessToken, deviceId) {
        when (val result = withContext(Dispatchers.IO) { api.getDevice(accessToken, deviceId) }) {
            is DashboardApi.Result.Success -> device = result.value
            is DashboardApi.Result.Failure -> error = result.message
        }
    }

    if (showRevokeConfirm) {
        AlertDialog(
            onDismissRequest = { if (!busy) showRevokeConfirm = false },
            title = { Text(strings.text("revoke_device")) },
            text = { Text(strings.text("dangerous_actions_scope")) },
            confirmButton = {
                TextButton(
                    enabled = !busy,
                    onClick = {
                        val current = device ?: return@TextButton
                        busy = true
                        scope.launch(Dispatchers.IO) {
                            val result = api.revokeDevice(accessToken, current.deviceId)
                            withContext(Dispatchers.Main) {
                                busy = false
                                showRevokeConfirm = false
                                when (result) {
                                    is DashboardApi.Result.Success -> onRevoked()
                                    is DashboardApi.Result.Failure -> error = result.message
                                }
                            }
                        }
                    },
                ) { Text(strings.text("revoke_device"), color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { showRevokeConfirm = false }, enabled = !busy) { Text(strings.text("cancel")) } },
        )
    }

    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(strings.text("device_identity"), style = MaterialTheme.typography.headlineLarge)
            Text(strings.text("device_identity_subtitle"), color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (device == null && error == null) CircularProgressIndicator()
            error?.let { Text(strings.text("load_failed", it), color = MaterialTheme.colorScheme.error) }
            message?.let { Text(it, color = MaterialTheme.colorScheme.secondary) }

            device?.let { current ->
                SentinelCard(kind = SentinelCardKind.DEVICE) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        StatusBadge(current.state, statusFromRaw(current.state))
                        StatusBadge(current.securityStatus, statusFromRaw(current.securityStatus))
                        Text(strings.text("platform", current.platform))
                        Text(strings.text("algorithm", current.algorithm))
                        DataText(strings.text("fingerprint", current.fingerprint))
                        DataText(strings.text("bound", current.boundAt ?: strings.text("not_available")))
                        DataText(strings.text("last_seen", current.lastSeenAt ?: strings.text("not_available")))
                    }
                }

                PrimaryButton(
                    text = strings.text("rotate_key"),
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                    onClick = {
                        busy = true; error = null; message = null
                        scope.launch(Dispatchers.IO) {
                            var rotated: DashboardApi.DeviceActionResult? = null
                            var failure: String? = null
                            var candidate: DeviceIdentity.RotationCandidate? = null
                            var requestStarted = false
                            try {
                                val prepared = deviceIdentity.prepareRotation()
                                candidate = prepared
                                requestStarted = true
                                when (val result = api.rotateDevice(accessToken, current.deviceId, current.platform, prepared.publicKeyDerBase64, prepared.fingerprint)) {
                                    is DashboardApi.Result.Success -> {
                                        val value = result.value
                                        if (value.deviceId.isNullOrBlank() || value.sessionToken.isNullOrBlank() || value.refreshToken.isNullOrBlank()) {
                                            failure = "KEY_ROTATION_RECOVERY_REQUIRED"
                                        } else {
                                            try {
                                                deviceIdentity.commitRotation(prepared)
                                                rotated = value
                                            } catch (_: Exception) {
                                                failure = "KEY_ROTATION_RECOVERY_REQUIRED"
                                            }
                                        }
                                    }
                                    is DashboardApi.Result.Failure -> failure = "KEY_ROTATION_RECOVERY_REQUIRED:${result.message}"
                                }
                            } catch (exception: Exception) {
                                if (!requestStarted) candidate?.let { runCatching { deviceIdentity.abortRotation(it) } }
                                failure = if (requestStarted) "KEY_ROTATION_RECOVERY_REQUIRED" else "KEY_ROTATION_${exception.javaClass.simpleName}"
                            }
                            withContext(Dispatchers.Main) {
                                busy = false
                                val value = rotated
                                if (value == null) error = failure ?: "KEY_ROTATION_FAILED"
                                else {
                                    message = strings.text("rotation_success")
                                    onRotated(value)
                                }
                            }
                        }
                    },
                )

                SentinelCard(kind = SentinelCardKind.CONTENT) {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(strings.text("dangerous_actions_scope"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        DangerButton(strings.text("revoke_device"), { showRevokeConfirm = true }, Modifier.fillMaxWidth(), !busy)
                    }
                }
            }
        }
    }
}
