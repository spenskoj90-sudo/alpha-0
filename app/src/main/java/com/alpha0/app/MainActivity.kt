package com.alpha0.app

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.ui.SentinelTheme

class MainActivity : ComponentActivity() {
    private val sessionStore = SecureSessionStore()
    private val deviceIdentity = DeviceIdentity()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val diag = DiagnosticLogger.get(this)
        diag.info(
            "APP",
            "APP_START",
            "SUCCESS",
            details = mapOf(
                "sdk" to android.os.Build.VERSION.SDK_INT,
                "model" to (android.os.Build.MODEL ?: "unknown").take(64)
            )
        )
        deviceIdentity.attachDiagnostics(this)

        val session = sessionStore.load(this)
        diag.info(
            "SESSION",
            "SESSION_LOAD",
            if (session != null) "SUCCESS" else "SKIPPED",
            details = mapOf(
                "has_session" to (session != null),
                "has_device_id" to (session?.deviceId != null)
            )
        )

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

                NavHost(
                    navController = navController,
                    startDestination = startDestination,
                    enterTransition = { fadeIn(animationSpec = tween(150)) },
                    exitTransition = { fadeOut(animationSpec = tween(150)) },
                    popEnterTransition = { fadeIn(animationSpec = tween(150)) },
                    popExitTransition = { fadeOut(animationSpec = tween(150)) },
                ) {
                    composable("login") {
                        LoginScreen(api = authApi) { authenticatedSession ->
                            diag.info("AUTH", "LOGIN_SUCCESS", "SUCCESS")
                            sessionStore.save(this@MainActivity, authenticatedSession.accessToken, authenticatedSession.refreshToken)
                            diag.info("SESSION", "SESSION_SAVE", "SUCCESS", details = mapOf("has_device_id" to false))
                            navController.navigate("device-setup") {
                                popUpTo("login") { inclusive = true }
                            }
                        }
                    }
                    composable("device-setup") {
                        val currentSession = sessionStore.load(this@MainActivity)
                        if (currentSession == null) {
                            diag.warn("SESSION", "SESSION_MISSING_ON_SETUP", "FAILURE")
                            navController.navigate("login") {
                                popUpTo("device-setup") { inclusive = true }
                            }
                        } else {
                            DeviceSetupScreen(
                                accessToken = currentSession.accessToken,
                                deviceIdentity = deviceIdentity,
                                api = deviceApi,
                                onBound = { deviceId ->
                                    diag.info("DEVICE", "BIND_SUCCESS", "SUCCESS", details = mapOf("device_id_prefix" to deviceId.take(12)))
                                    sessionStore.save(
                                        this@MainActivity,
                                        currentSession.accessToken,
                                        currentSession.refreshToken,
                                        deviceId
                                    )
                                    diag.info("SESSION", "SESSION_SAVE", "SUCCESS", details = mapOf("has_device_id" to true))
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
                            diag.warn("SESSION", "SESSION_MISSING_ON_DASHBOARD", "FAILURE")
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
                                    diag.info("DEVICE", "REVOKE", "SUCCESS")
                                    sessionStore.clear(this@MainActivity)
                                    diag.info("SESSION", "SESSION_CLEAR", "SUCCESS")
                                    navController.navigate("login") {
                                        popUpTo("login") { inclusive = true }
                                    }
                                },
                                onRotated = { rotated ->
                                    val newDeviceId = rotated.deviceId
                                    val newAccessToken = rotated.sessionToken
                                    val newRefreshToken = rotated.refreshToken
                                    if (!newDeviceId.isNullOrBlank() && !newAccessToken.isNullOrBlank() && !newRefreshToken.isNullOrBlank()) {
                                        diag.info("DEVICE", "ROTATE", "SUCCESS", details = mapOf("device_id_prefix" to newDeviceId.take(12)))
                                        sessionStore.save(this@MainActivity, newAccessToken, newRefreshToken, newDeviceId)
                                        navController.navigate("dashboard/${Uri.encode(newDeviceId)}") {
                                            popUpTo("device-details/${Uri.encode(deviceId)}") { inclusive = true }
                                        }
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
