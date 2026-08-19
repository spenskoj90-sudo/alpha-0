package com.alpha0.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.CharacterDashboard
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
                    CharacterDashboard(
                        characterName = "Operator",
                        level = 27,
                        health = 94,
                        energy = 82,
                        syncState = "ACCOUNT AUTHENTICATED — DEVICE FLOW NEXT"
                    )
                } else {
                    LoginScreen(api = api) { session ->
                        sessionStore.save(this, session.accessToken, session.refreshToken)
                        authenticated = true
                    }
                }
            }
        }
    }
}
