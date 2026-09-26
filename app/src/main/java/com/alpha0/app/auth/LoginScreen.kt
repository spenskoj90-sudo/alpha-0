package com.alpha0.app.auth

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.alpha0.app.R
import com.alpha0.app.ui.GhostButton
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.SecondaryButton
import com.alpha0.app.ui.assertiveStatusSemantics
import com.alpha0.app.ui.progressStatusSemantics
import kotlinx.coroutines.launch

private enum class AuthMode { SIGN_IN, REGISTER, RESET, VERIFY_EMAIL, MFA }

@Composable
fun LoginScreen(
    api: AuthApi,
    federatedAuth: FederatedAuthCoordinator,
    federatedCallbackUri: Uri?,
    onFederatedCallbackConsumed: () -> Unit,
    onAuthenticated: (AuthApi.Session) -> Unit,
) {
    val strings = LocalAppStrings.current
    val context = LocalContext.current
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var actionCode by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var mode by remember { mutableStateOf(AuthMode.SIGN_IN) }
    var resetCodeRequested by remember { mutableStateOf(false) }
    var pendingSession by remember { mutableStateOf<AuthApi.Session?>(null) }
    var mfaChallenge by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var status by remember { mutableStateOf<String?>(null) }
    var providerStatuses by remember { mutableStateOf<List<AuthApi.ProviderStatus>>(emptyList()) }
    var coreReady by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        status = strings.text("core_starting")
        when (api.coreReadiness()) {
            AuthApi.CoreReadinessResult.Success -> {
                coreReady = true
                status = null
                providerStatuses = when (val result = api.providerCatalog()) {
                    is AuthApi.ProviderCatalogResult.Success -> result.providers.filter {
                        it.enabled && federatedAuth.isProviderCompatible(it)
                    }
                    is AuthApi.ProviderCatalogResult.Failure -> emptyList()
                }
            }
            is AuthApi.CoreReadinessResult.Failure -> {
                status = strings.text("core_retry_on_action")
            }
        }
    }

    LaunchedEffect(federatedCallbackUri) {
        val callback = federatedCallbackUri ?: return@LaunchedEffect
        busy = true
        error = null
        status = strings.text("federated_completing")
        val result = federatedAuth.completeBrowserCallback(callback)
        onFederatedCallbackConsumed()
        busy = false
        status = null
        when (result) {
            is AuthApi.Result.Success -> onAuthenticated(result.session)
            is AuthApi.Result.MfaRequired -> {
                mfaChallenge = result.challengeToken
                actionCode = ""
                mode = AuthMode.MFA
                status = strings.text("mfa_required")
            }
            is AuthApi.Result.Failure -> error = when (result.message) {
                "AUTH_PROVIDER_CANCELLED" -> strings.text("federated_cancelled")
                "ACCOUNT_LINK_REQUIRED" -> strings.text("account_link_required")
                "AUTH_CALLBACK_EXPIRED" -> strings.text("federated_expired")
                else -> strings.text("federated_failed", result.message)
            }
        }
    }

    fun actionError(message: String): String = when (message) {
        "AUTH_ACTION_TOKEN_INVALID" -> strings.text("auth_code_invalid")
        "REQUEST_TIMEOUT" -> strings.text("request_timeout")
        "NETWORK_ERROR" -> strings.text("server_unreachable")
        else -> strings.text("auth_failed", message)
    }

    suspend fun ensureCoreReady(): Boolean {
        if (coreReady) return true
        status = strings.text("core_starting")
        error = null
        return when (val readiness = api.coreReadiness()) {
            AuthApi.CoreReadinessResult.Success -> {
                coreReady = true
                status = null
                true
            }
            is AuthApi.CoreReadinessResult.Failure -> {
                status = null
                error = when (readiness.message) {
                    "REQUEST_TIMEOUT" -> strings.text("request_timeout")
                    else -> strings.text("server_unreachable")
                }
                false
            }
        }
    }

    fun handleFederatedResult(result: AuthApi.Result) {
        busy = false
        status = null
        when (result) {
            is AuthApi.Result.Success -> onAuthenticated(result.session)
            is AuthApi.Result.MfaRequired -> {
                mfaChallenge = result.challengeToken
                actionCode = ""
                mode = AuthMode.MFA
                status = strings.text("mfa_required")
            }
            is AuthApi.Result.Failure -> error = when (result.message) {
                "GOOGLE_CREDENTIAL_CANCELLED", "AUTH_PROVIDER_CANCELLED" -> strings.text("federated_cancelled")
                "ACCOUNT_LINK_REQUIRED" -> strings.text("account_link_required")
                "AUTH_PROVIDER_NOT_CONFIGURED" -> strings.text("provider_not_configured")
                else -> strings.text("federated_failed", result.message)
            }
        }
    }

    fun signInWithGoogle() {
        busy = true
        error = null
        status = strings.text("federated_opening", "Google")
        scope.launch {
            handleFederatedResult(federatedAuth.signInWithGoogle())
        }
    }

    fun openBrowserProvider(provider: String) {
        busy = true
        error = null
        val displayName = if (provider == "telegram") "Telegram" else "VK"
        status = strings.text("federated_opening", displayName)
        scope.launch {
            when (val result = federatedAuth.beginBrowser(provider)) {
                is FederatedAuthCoordinator.BrowserLaunchResult.Failure -> {
                    busy = false
                    status = null
                    error = strings.text("federated_failed", result.message)
                }
                is FederatedAuthCoordinator.BrowserLaunchResult.Success -> {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(result.value.url))
                    val launched = runCatching {
                        context.startActivity(intent)
                    }.isSuccess
                    busy = false
                    if (launched) {
                        status = strings.text("federated_return_hint", displayName)
                    } else {
                        federatedAuth.cancelPendingBrowserFlow()
                        status = null
                        error = strings.text("browser_unavailable")
                    }
                }
            }
        }
    }

    fun submitCredentials() {
        val normalizedEmail = email.trim().lowercase()
        when {
            !normalizedEmail.contains("@") -> error = strings.text("valid_email")
            password.length < 12 -> error = strings.text("password_length")
            else -> {
                busy = true
                error = null
                status = null
                scope.launch {
                    if (!ensureCoreReady()) {
                        busy = false
                        return@launch
                    }
                    val result = if (mode == AuthMode.REGISTER) {
                        api.register(normalizedEmail, password)
                    } else {
                        api.login(normalizedEmail, password)
                    }
                    busy = false
                    when (result) {
                        is AuthApi.Result.Success -> {
                            if (mode == AuthMode.REGISTER) {
                                pendingSession = result.session
                                actionCode = ""
                                mode = AuthMode.VERIFY_EMAIL
                                status = strings.text("verification_pending_delivery")
                            } else {
                                onAuthenticated(result.session)
                            }
                        }
                        is AuthApi.Result.MfaRequired -> {
                            mfaChallenge = result.challengeToken
                            password = ""
                            actionCode = ""
                            mode = AuthMode.MFA
                            status = strings.text("mfa_required")
                        }
                        is AuthApi.Result.Failure -> error = when (result.message) {
                            "INVALID_CREDENTIALS" -> strings.text("invalid_credentials")
                            "EMAIL_ALREADY_REGISTERED" -> strings.text("email_exists")
                            "REGISTER_OUTCOME_UNKNOWN" -> strings.text("register_unknown")
                            "REQUEST_TIMEOUT" -> strings.text("request_timeout")
                            "NETWORK_ERROR" -> strings.text("server_unreachable")
                            else -> strings.text("auth_failed", result.message)
                        }
                    }
                }
            }
        }
    }

    fun completeMfa() {
        val challenge = mfaChallenge
        if (challenge.isNullOrBlank()) {
            mode = AuthMode.SIGN_IN
            error = strings.text("mfa_expired")
            return
        }
        if (actionCode.trim().length < 6) {
            error = strings.text("mfa_code_required")
            return
        }
        busy = true
        error = null
        scope.launch {
            when (val result = api.completeMfa(challenge, actionCode)) {
                is AuthApi.Result.Success -> onAuthenticated(result.session)
                is AuthApi.Result.MfaRequired -> {
                    mfaChallenge = result.challengeToken
                    actionCode = ""
                    error = strings.text("mfa_invalid")
                }
                is AuthApi.Result.Failure -> error = when (result.message) {
                    "MFA_INVALID" -> strings.text("mfa_invalid")
                    "REQUEST_TIMEOUT" -> strings.text("request_timeout")
                    "NETWORK_ERROR" -> strings.text("server_unreachable")
                    else -> strings.text("auth_failed", result.message)
                }
            }
            busy = false
        }
    }

    fun requestReset() {
        val normalizedEmail = email.trim().lowercase()
        if (!normalizedEmail.contains("@")) {
            error = strings.text("valid_email")
            return
        }
        busy = true
        error = null
        status = null
        scope.launch {
            if (!ensureCoreReady()) {
                busy = false
                return@launch
            }
            when (val result = api.requestPasswordReset(normalizedEmail)) {
                is AuthApi.ActionResult.Success -> {
                    resetCodeRequested = true
                    status = strings.text("reset_sent")
                }
                is AuthApi.ActionResult.Failure -> error = actionError(result.message)
            }
            busy = false
        }
    }

    fun confirmReset() {
        when {
            actionCode.trim().length < 32 -> error = strings.text("auth_code_required")
            password.length < 12 -> error = strings.text("password_length")
            else -> {
                busy = true
                error = null
                status = null
                scope.launch {
                    when (val result = api.confirmPasswordReset(actionCode, password)) {
                        is AuthApi.ActionResult.Success -> {
                            mode = AuthMode.SIGN_IN
                            resetCodeRequested = false
                            actionCode = ""
                            password = ""
                            status = strings.text("password_reset_complete")
                        }
                        is AuthApi.ActionResult.Failure -> error = actionError(result.message)
                    }
                    busy = false
                }
            }
        }
    }

    fun confirmVerification() {
        if (actionCode.trim().length < 32) {
            error = strings.text("auth_code_required")
            return
        }
        busy = true
        error = null
        scope.launch {
            when (val result = api.confirmEmailVerification(actionCode)) {
                is AuthApi.ActionResult.Success -> {
                    val session = pendingSession
                    if (session != null) onAuthenticated(session)
                    else {
                        mode = AuthMode.SIGN_IN
                        status = strings.text("email_verified")
                    }
                }
                is AuthApi.ActionResult.Failure -> error = actionError(result.message)
            }
            busy = false
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Image(
                painter = painterResource(R.drawable.sentinel_master_icon),
                contentDescription = null,
                modifier = Modifier.size(104.dp),
                contentScale = ContentScale.Fit,
            )
            Text(strings.text("app_name"), style = MaterialTheme.typography.headlineMedium)
            Text(
                strings.text(
                    when (mode) {
                        AuthMode.SIGN_IN -> "sign_in_title"
                        AuthMode.REGISTER -> "create_account_title"
                        AuthMode.RESET -> "reset_password_title"
                        AuthMode.VERIFY_EMAIL -> "verify_email_title"
                        AuthMode.MFA -> "mfa_title"
                    }
                ),
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                strings.text(
                    when (mode) {
                        AuthMode.RESET -> "reset_password_explanation"
                        AuthMode.VERIFY_EMAIL -> "verify_email_explanation"
                        AuthMode.MFA -> "mfa_explanation"
                        else -> "auth_explanation"
                    }
                ),
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (mode != AuthMode.VERIFY_EMAIL && mode != AuthMode.MFA) {
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it; error = null; status = null },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(strings.text("email")) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    enabled = !busy,
                    shape = RoundedCornerShape(6.dp),
                )
            }

            if (mode == AuthMode.RESET && resetCodeRequested || mode == AuthMode.VERIFY_EMAIL || mode == AuthMode.MFA) {
                OutlinedTextField(
                    value = actionCode,
                    onValueChange = { actionCode = it.trim(); error = null },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(strings.text(if (mode == AuthMode.MFA) "mfa_code" else "auth_code")) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
                    enabled = !busy,
                    shape = RoundedCornerShape(6.dp),
                )
            }

            if (mode == AuthMode.SIGN_IN || mode == AuthMode.REGISTER || (mode == AuthMode.RESET && resetCodeRequested)) {
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it; error = null; status = null },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(strings.text(if (mode == AuthMode.RESET) "new_password" else "password")) },
                    singleLine = true,
                    visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    trailingIcon = {
                        IconButton(onClick = { passwordVisible = !passwordVisible }, enabled = !busy) {
                            Icon(
                                imageVector = if (passwordVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                contentDescription = strings.text(if (passwordVisible) "hide_password" else "show_password"),
                            )
                        }
                    },
                    enabled = !busy,
                    shape = RoundedCornerShape(6.dp),
                )
            }

            status?.let {
                Text(it, color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.bodyMedium)
            }
            error?.let {
                Text(
                    it,
                    modifier = Modifier.assertiveStatusSemantics(),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            Button(
                onClick = {
                    when (mode) {
                        AuthMode.SIGN_IN, AuthMode.REGISTER -> submitCredentials()
                        AuthMode.RESET -> if (resetCodeRequested) confirmReset() else requestReset()
                        AuthMode.VERIFY_EMAIL -> confirmVerification()
                        AuthMode.MFA -> completeMfa()
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                shape = RoundedCornerShape(6.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(
                        modifier = Modifier.progressStatusSemantics(strings.text("working")),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(
                        strings.text(
                            when (mode) {
                                AuthMode.SIGN_IN -> "sign_in"
                                AuthMode.REGISTER -> "create_account"
                                AuthMode.RESET -> if (resetCodeRequested) "reset_password" else "send_reset_code"
                                AuthMode.VERIFY_EMAIL -> "verify_email"
                                AuthMode.MFA -> "verify_mfa"
                            }
                        )
                    )
                }
            }

            if ((mode == AuthMode.SIGN_IN || mode == AuthMode.REGISTER) && providerStatuses.isNotEmpty()) {
                Text(
                    strings.text("or_continue_with"),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (providerStatuses.any { it.provider == "google" }) {
                    SecondaryButton(strings.text("continue_google"), ::signInWithGoogle, Modifier.fillMaxWidth(), !busy)
                }
                if (providerStatuses.any { it.provider == "telegram" }) {
                    SecondaryButton(strings.text("continue_telegram"), { openBrowserProvider("telegram") }, Modifier.fillMaxWidth(), !busy)
                }
                if (providerStatuses.any { it.provider == "vk" }) {
                    SecondaryButton(strings.text("continue_vk"), { openBrowserProvider("vk") }, Modifier.fillMaxWidth(), !busy)
                }
                Text(
                    strings.text("federated_privacy"),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            when (mode) {
                AuthMode.SIGN_IN -> {
                    GhostButton(
                        text = strings.text("new_account"),
                        onClick = { mode = AuthMode.REGISTER; error = null; status = null },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !busy,
                    )
                    GhostButton(
                        text = strings.text("forgot_password"),
                        onClick = {
                            mode = AuthMode.RESET
                            resetCodeRequested = false
                            password = ""
                            actionCode = ""
                            error = null
                            status = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !busy,
                    )
                }
                AuthMode.REGISTER -> GhostButton(
                    text = strings.text("existing_account"),
                    onClick = { mode = AuthMode.SIGN_IN; error = null; status = null },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy,
                )
                AuthMode.RESET -> GhostButton(
                    text = strings.text("back_to_sign_in"),
                    onClick = {
                        mode = AuthMode.SIGN_IN
                        resetCodeRequested = false
                        actionCode = ""
                        password = ""
                        error = null
                        status = null
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy,
                )
                AuthMode.MFA -> GhostButton(
                    text = strings.text("back_to_sign_in"),
                    onClick = {
                        mfaChallenge = null
                        actionCode = ""
                        mode = AuthMode.SIGN_IN
                        error = null
                        status = null
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !busy,
                )
                AuthMode.VERIFY_EMAIL -> {
                    GhostButton(
                        text = strings.text("resend_code"),
                        onClick = {
                            busy = true
                            error = null
                            scope.launch {
                                val session = pendingSession
                                val result = if (session != null) {
                                    api.requestAccountEmailVerification(session.accessToken)
                                } else {
                                    api.requestEmailVerification(email)
                                }
                                when (result) {
                                    is AuthApi.ActionResult.Success -> {
                                        status = if (session != null) strings.text("verification_sent")
                                        else strings.text("verification_pending_delivery")
                                    }
                                    is AuthApi.ActionResult.Failure -> {
                                        error = if (result.message == "EMAIL_PROVIDER_UNAVAILABLE") {
                                            strings.text("email_delivery_unavailable")
                                        } else {
                                            actionError(result.message)
                                        }
                                    }
                                }
                                busy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !busy,
                    )
                    GhostButton(
                        text = strings.text("verify_later"),
                        onClick = { pendingSession?.let(onAuthenticated) ?: run { mode = AuthMode.SIGN_IN } },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = !busy,
                    )
                }
            }
        }
    }
}
