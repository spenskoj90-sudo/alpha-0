package com.alpha0.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.SentinelTheme

class MainActivity : ComponentActivity() {
    private val sessionStore = SecureSessionStore()
    private var authenticated by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        authenticated = sessionStore.load(this) != null
        val api = AuthApi(BuildConfig.SENTINEL_API_BASE_URL)
        setContent {
            SentinelTheme {
                if (authenticated) {
                    AccountReadyScreen(onContinue = { /* device enrollment is the next implemented flow */ })
                } else {
                    LoginScreen(api = api) { session ->
                        sessionStore.save(this, session.accessToken)
                        authenticated = true
                    }
                }
            }
        }
    }
}

@androidx.compose.runtime.Composable
private fun AccountReadyScreen(onContinue: () -> Unit) {
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("ACCOUNT READY", style = MaterialTheme.typography.headlineMedium)
            Text(
                "You are authenticated. This account session is stored securely on the device. Device enrollment is the next step.",
                style = MaterialTheme.typography.bodyLarge,
            )
            Button(onClick = onContinue) {
                Text("Continue")
            }
        }
    }
}
