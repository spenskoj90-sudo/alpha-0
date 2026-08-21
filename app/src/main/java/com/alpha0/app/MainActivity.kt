package com.alpha0.app

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.remember
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.dashboard.DashboardApi
import com.alpha0.app.dashboard.DashboardScreen
import com.alpha0.app.dashboard.DeviceDetailsScreen
import com.alpha0.app.dashboard.GameDetailsScreen
import com.alpha0.app.device.DeviceApi
import com.alpha0.app.device.DeviceSetupScreen
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.SentinelTheme

class MainActivity : ComponentActivity() {
    private val sessionStore = SecureSessionStore()
    private val deviceIdentity = DeviceIdentity()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val session = sessionStore.load(this)
        val authApi = AuthApi(BuildConfig.SENTINEL_API_BASE_URL)
        val deviceApi = DeviceApi(BuildConfig.SENTINEL_API_BASE_URL)
        val dashboardApi = DashboardApi(BuildConfig.SENTINEL_API_BASE_URL)

        setContent {
            SentinelTheme {
                val navController = rememberNavController()
                val startDestination = remember(session) {
                    when {
                        session == null -> "login"
                        session.deviceId.isNullOrBlank() -> "device-setup"
                        else -> "dashboard/${Uri.encode(session.deviceId)}"
                    }
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
                                onBound = { deviceId ->
                                    sessionStore.save(
                                        this@MainActivity,
                                        currentSession.accessToken,
                                        currentSession.refreshToken,
                                        deviceId
                                    )
                                    navController.navigate("dashboard/${Uri.encode(deviceId)}") {
                                        popUpTo("device-setup") { inclusive = true }
                                    }
                                }
                            )
                        }
                    }
                    composable(
                        route = "dashboard/{deviceId}",
                        arguments = listOf(navArgument("deviceId") { type = NavType.StringType })
                    ) { entry ->
                        val currentSession = sessionStore.load(this@MainActivity)
                        val deviceId = entry.arguments?.getString("deviceId")
                        if (currentSession == null || deviceId.isNullOrBlank()) {
                            navController.navigate("login") { popUpTo("login") { inclusive = true } }
                        } else {
                            DashboardScreen(
                                accessToken = currentSession.accessToken,
                                deviceId = deviceId,
                                api = dashboardApi,
                                onDeviceClick = { navController.navigate("device-details/${Uri.encode(deviceId)}") },
                                onGameClick = { entitlementId -> navController.navigate("game-details/${Uri.encode(entitlementId)}") }
                            )
                        }
                    }
                    composable(
                        route = "device-details/{deviceId}",
                        arguments = listOf(navArgument("deviceId") { type = NavType.StringType })
                    ) { entry ->
                        val currentSession = sessionStore.load(this@MainActivity)
                        val deviceId = entry.arguments?.getString("deviceId")
                        if (currentSession == null || deviceId.isNullOrBlank()) {
                            navController.navigate("login") { popUpTo("login") { inclusive = true } }
                        } else {
                            DeviceDetailsScreen(
                                accessToken = currentSession.accessToken,
                                deviceId = deviceId,
                                api = dashboardApi,
                                onRevoked = {
                                    sessionStore.clear(this@MainActivity)
                                    navController.navigate("login") {
                                        popUpTo(0) { inclusive = true }
                                    }
                                }
                            )
                        }
                    }
                    composable(
                        route = "game-details/{entitlementId}",
                        arguments = listOf(navArgument("entitlementId") { type = NavType.StringType })
                    ) { entry ->
                        val currentSession = sessionStore.load(this@MainActivity)
                        val entitlementId = entry.arguments?.getString("entitlementId")
                        if (currentSession == null || entitlementId.isNullOrBlank()) {
                            navController.navigate("login") { popUpTo("login") { inclusive = true } }
                        } else {
                            GameDetailsScreen(accessToken = currentSession.accessToken, entitlementId = entitlementId, api = dashboardApi)
                        }
                    }
                }
            }
        }
    }
}
