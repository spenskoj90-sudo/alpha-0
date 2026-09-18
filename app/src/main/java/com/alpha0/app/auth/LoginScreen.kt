package com.alpha0.app.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.SentinelColors
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.assertiveStatusSemantics
import com.alpha0.app.ui.progressStatusSemantics
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    api: AuthApi,
    onAuthenticated: (AuthApi.Session) -> Unit,
) {
    val strings = LocalAppStrings.current
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var registerMode by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun submit() {
        val normalizedEmail = email.trim().lowercase()
        when {
            !normalizedEmail.contains("@") -> error = strings.text("valid_email")
            password.length < 12 -> error = strings.text("password_length")
            else -> {
                busy = true
                error = null
                scope.launch {
                    val result = if (registerMode) {
                        api.register(normalizedEmail, password)
                    } else {
                        api.login(normalizedEmail, password)
                    }
                    busy = false
                    when (result) {
                        is AuthApi.Result.Success -> onAuthenticated(result.session)
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

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(strings.text("app_name"), style = MaterialTheme.typography.headlineLarge)
            Text(
                strings.text(if (registerMode) "create_account_title" else "sign_in_title"),
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                strings.text("auth_explanation"),
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            OutlinedTextField(
                value = email,
                onValueChange = { email = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text(strings.text("email")) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                enabled = !busy,
                shape = RoundedCornerShape(12.dp),
            )

            OutlinedTextField(
                value = password,
                onValueChange = { password = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text(strings.text("password")) },
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
                shape = RoundedCornerShape(12.dp),
            )

            if (error != null) {
                Text(
                    error!!,
                    modifier = Modifier.assertiveStatusSemantics(),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            Button(
                onClick = ::submit,
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                shape = RoundedCornerShape(14.dp),
                colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            ) {
                if (busy) {
                    CircularProgressIndicator(
                        modifier = Modifier.progressStatusSemantics(
                            strings.text(if (registerMode) "create_account" else "sign_in")
                        ),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(strings.text(if (registerMode) "create_account" else "sign_in"))
                }
            }

            OutlinedButton(
                onClick = { registerMode = !registerMode; error = null },
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(strings.text(if (registerMode) "existing_account" else "new_account"))
            }
        }
    }
}
