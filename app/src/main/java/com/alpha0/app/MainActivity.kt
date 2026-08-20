package com.alpha0.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.remember
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.device.DeviceApi
import com.alpha0.app.device.DeviceSetupScreen
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.CharacterDashboard
import com.alpha0.app.ui.SentinelTheme

class MainActivity : ComponentActivity() {
    private val sessionStore = SecureSessionStore()
    private val deviceIdentity = DeviceIdentity()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val session = sessionStore.load(this)
        val authApi = AuthApi(BuildConfig.SENTINEL_API_BASE_URL)
        val deviceApi = DeviceApi(BuildConfig.SENTINEL_API_BASE_URL)

        setContent {
            SentinelTheme {
                val navController = rememberNavController()
                val startDestination = remember(session) {
                    if (session == null) "login" else "device-setup"
                }

                NavHost(navController = navController, startDestination = startDestination) {
                    composable("login") {
                        LoginScreen(api = authApi) { authenticatedSession ->
                            sessionStore.save(this@MainActivity, authenticatedSession.accessToken, authenticatedSession.refreshToken)
                            navController.navigate("device-setup") {
                                popUpTo("login") { inclusive = true }
                            }
                        }
                    }
                    composable("device-setup") {
                        val currentSession = sessionStore.load(this@MainActivity)
                        if (currentSession == null) {
                            navController.navigate("login") {
                                popUpTo("device-setup") { inclusive = true }
                            }
                        } else {
                            DeviceSetupScreen(
                                accessToken = currentSession.accessToken,
                                deviceIdentity = deviceIdentity,
                                api = deviceApi,
                                onBound = {
                                    navController.navigate("dashboard") {
                                        popUpTo("device-setup") { inclusive = true }
                                    }
                                }
                            )
                        }
                    }
                    composable("dashboard") {
                        CharacterDashboard(
                            characterName = "Operator",
                            level = 27,
                            health = 94,
                            energy = 82,
                            syncState = "DEVICE BOUND — DASHBOARD"
                        )
                    }
                }
            }
        }
    }
}
