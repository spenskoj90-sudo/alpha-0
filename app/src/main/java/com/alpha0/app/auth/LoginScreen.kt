package com.alpha0.app.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.alpha0.app.ui.SentinelAmber
import com.alpha0.app.ui.SentinelDanger
import com.alpha0.app.ui.SentinelTextSecondary
import com.alpha0.app.ui.SentinelBackground

@Composable
fun LoginScreen(
    api: AuthApi,
    onAuthenticated: (AuthApi.Session) -> Unit,
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var registerMode by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    fun submit() {
        val normalizedEmail = email.trim().lowercase()
        when {
            !normalizedEmail.contains("@") -> error = "Enter a valid email address"
            password.length < 12 -> error = "Password must be at least 12 characters"
            else -> {
                busy = true
                error = null
                Thread {
                    val result = if (registerMode) api.register(normalizedEmail, password) else api.login(normalizedEmail, password)
                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                        busy = false
                        when (result) {
                            is AuthApi.Result.Success -> onAuthenticated(result.session)
                            is AuthApi.Result.Failure -> error = when (result.message) {
                                "INVALID_CREDENTIALS" -> "Email or password is incorrect"
                                "EMAIL_ALREADY_REGISTERED" -> "An account with this email already exists"
                                "NETWORK_ERROR" -> "Cannot reach SENTINEL server"
                                else -> "Authentication failed: ${result.message}"
                            }
                        }
                    }
                }.start()
            }
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("SENTINEL", style = MaterialTheme.typography.displaySmall)
            Text(
                if (registerMode) "CREATE ACCOUNT" else "SIGN IN",
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                "Your account is separate from this device identity. Device enrollment follows after authentication.",
                style = MaterialTheme.typography.bodyMedium,
                color = SentinelTextSecondary,
            )

            OutlinedTextField(
                value = email,
                onValueChange = { email = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Email") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                enabled = !busy,
            )

            OutlinedTextField(
                value = password,
                onValueChange = { password = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Password") },
                singleLine = true,
                visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                trailingIcon = {
                    IconButton(onClick = { passwordVisible = !passwordVisible }, enabled = !busy) {
                        Icon(
                            imageVector = if (passwordVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                            contentDescription = if (passwordVisible) "Hide password" else "Show password",
                        )
                    }
                },
                enabled = !busy,
            )

            if (error != null) {
                Text(error!!, color = SentinelDanger, style = MaterialTheme.typography.bodyMedium)
            }

            Button(
                onClick = ::submit,
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                colors = ButtonDefaults.buttonColors(containerColor = SentinelAmber, contentColor = SentinelBackground),
            ) {
                if (busy) CircularProgressIndicator(strokeWidth = 2.dp, color = SentinelBackground) else Text(if (registerMode) "Create account" else "Sign in")
            }

            OutlinedButton(
                onClick = { registerMode = !registerMode; error = null },
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
            ) {
                Text(if (registerMode) "I already have an account" else "Create a new account")
            }
        }
    }
}
