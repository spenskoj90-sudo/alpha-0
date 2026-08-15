package com.alpha0.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.alpha0.app.network.SentinelApiClient
import java.util.concurrent.Executors

@Composable
fun LoginScreen(
    api: SentinelApiClient,
    onAuthenticated: (SentinelApiClient.Session) -> Unit
) {
    var registerMode by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val executor = remember { Executors.newSingleThreadExecutor() }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("SENTINEL", style = MaterialTheme.typography.headlineMedium)
            Text(
                if (registerMode) "Create account" else "Sign in",
                style = MaterialTheme.typography.headlineSmall
            )
            Text(
                if (registerMode) "Create your Sentinel account before registering this device."
                else "Sign in to manage your device protection and game access.",
                style = MaterialTheme.typography.bodyMedium
            )

            OutlinedTextField(
                value = email,
                onValueChange = { email = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Email") },
                singleLine = true,
                enabled = !busy
            )
            OutlinedTextField(
                value = password,
                onValueChange = { password = it; error = null },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Password") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                enabled = !busy
            )

            error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
            }

            Button(
                onClick = {
                    val cleanEmail = email.trim()
                    when {
                        !cleanEmail.contains("@") -> error = "Enter a valid email address."
                        password.length < 12 -> error = "Password must contain at least 12 characters."
                        else -> {
                            busy = true
                            error = null
                            executor.execute {
                                try {
                                    val session = if (registerMode) api.register(cleanEmail, password) else api.login(cleanEmail, password)
                                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                                        busy = false
                                        onAuthenticated(session)
                                    }
                                } catch (ex: SentinelApiClient.ApiException) {
                                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                                        busy = false
                                        error = when (ex.code) {
                                            "EMAIL_ALREADY_REGISTERED" -> "An account with this email already exists."
                                            "INVALID_CREDENTIALS" -> "Email or password is incorrect."
                                            else -> ex.message
                                        }
                                    }
                                } catch (_: Exception) {
                                    android.os.Handler(android.os.Looper.getMainLooper()).post {
                                        busy = false
                                        error = "Cannot reach SENTINEL Core. Check that the backend is running on this phone."
                                    }
                                }
                            }
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy
            ) {
                if (busy) CircularProgressIndicator() else Text(if (registerMode) "Create account" else "Sign in")
            }

            TextButton(
                onClick = { registerMode = !registerMode; error = null },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (registerMode) "Already have an account? Sign in" else "Need an account? Register")
            }
        }
    }
}
