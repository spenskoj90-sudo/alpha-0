package com.alpha0.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.alpha0.app.auth.AuthApi
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.auth.SessionManager
import com.alpha0.app.dashboard.ActivityScreen
import com.alpha0.app.dashboard.DashboardApi
import com.alpha0.app.dashboard.DashboardScreen
import com.alpha0.app.dashboard.DeviceDetailsScreen
import com.alpha0.app.dashboard.GameDetailsScreen
import com.alpha0.app.dashboard.GamesScreen
import com.alpha0.app.device.DeviceApi
import com.alpha0.app.device.DeviceSetupScreen
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.help.AboutScreen
import com.alpha0.app.help.HelpScreen
import com.alpha0.app.net.UrlConnectionHttpTransport
import com.alpha0.app.quality.QualityReportApi
import com.alpha0.app.quality.QualityReportScreen
import com.alpha0.app.security.DeviceIdentity
import com.alpha0.app.security.SecureSessionStore
import com.alpha0.app.settings.SettingsScreen
import com.alpha0.app.ui.AppLanguage
import com.alpha0.app.ui.AppPreferences
import com.alpha0.app.ui.AppThemeMode
import com.alpha0.app.ui.LocalAppStrings
import com.alpha0.app.ui.PrimaryDestinations
import com.alpha0.app.ui.SentinelBottomBar
import com.alpha0.app.ui.SentinelTheme
import com.alpha0.app.ui.SentinelTopBar
import com.alpha0.app.ui.rememberAppStrings
import com.alpha0.app.update.UpdateScreen

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
                "model" to (android.os.Build.MODEL ?: "unknown").take(64),
                "diagnostics_mode" to diag.mode(),
                "build_type" to BuildConfig.BUILD_TYPE,
            ),
        )
        deviceIdentity.attachDiagnostics(this)

        val initialSession = sessionStore.load(this)
        val preferences = AppPreferences(this)
        val httpTransport = UrlConnectionHttpTransport(readTimeoutMs = BuildConfig.SENTINEL_HTTP_READ_TIMEOUT_MS)
        val authApi = AuthApi(BuildConfig.SENTINEL_API_BASE_URL, httpTransport).also { it.attachDiagnostics(this) }
        val sessionManager = SessionManager(authApi, sessionStore)
        val deviceApi = DeviceApi(BuildConfig.SENTINEL_API_BASE_URL, httpTransport).also { it.attachDiagnostics(this) }
        val dashboardApi = DashboardApi(BuildConfig.SENTINEL_API_BASE_URL, httpTransport).also { it.attachDiagnostics(this) }
        val qualityReportApi = QualityReportApi(BuildConfig.SENTINEL_API_BASE_URL, diag, httpTransport)

        setContent {
            var language by remember { mutableStateOf(preferences.language()) }
            var theme by remember { mutableStateOf(preferences.theme()) }
            val strings = rememberAppStrings(language)
            CompositionLocalProvider(LocalAppStrings provides strings) {
                SentinelTheme(theme) {
                    SentinelApplicationUi(
                        initialSession = initialSession,
                        language = language,
                        theme = theme,
                        onLanguage = {
                            preferences.setLanguage(it)
                            language = it
                            diag.info("UI", "LANGUAGE_CHANGED", details = mapOf("language" to it.name))
                        },
                        onTheme = {
                            preferences.setTheme(it)
                            theme = it
                            diag.info("UI", "THEME_CHANGED", details = mapOf("theme" to it.name))
                        },
                        authApi = authApi,
                        sessionManager = sessionManager,
                        deviceApi = deviceApi,
                        dashboardApi = dashboardApi,
                        qualityReportApi = qualityReportApi,
                        sessionStore = sessionStore,
                        deviceIdentity = deviceIdentity,
                        diagnostics = diag,
                    )
                }
            }
        }
    }
}

@Composable
private fun SentinelApplicationUi(
    initialSession: SecureSessionStore.Companion.Session?,
    language: AppLanguage,
    theme: AppThemeMode,
    onLanguage: (AppLanguage) -> Unit,
    onTheme: (AppThemeMode) -> Unit,
    authApi: AuthApi,
    sessionManager: SessionManager,
    deviceApi: DeviceApi,
    dashboardApi: DashboardApi,
    qualityReportApi: QualityReportApi,
    sessionStore: SecureSessionStore,
    deviceIdentity: DeviceIdentity,
    diagnostics: DiagnosticLogger,
) {
    val activity = androidx.compose.ui.platform.LocalContext.current as ComponentActivity
    val strings = LocalAppStrings.current
    val navController = rememberNavController()
    var activeSession by remember { mutableStateOf(initialSession) }
    var refreshComplete by remember { mutableStateOf(initialSession == null) }

    LaunchedEffect(initialSession?.refreshToken) {
        if (initialSession == null) {
            refreshComplete = true
        } else {
            diagnostics.info("SESSION", "REFRESH_START")
            sessionManager.refreshStoredSession(activity)
            activeSession = sessionStore.load(activity)
            refreshComplete = true
            diagnostics.info("SESSION", "REFRESH_COMPLETE", if (activeSession != null) "SUCCESS" else "FAILURE")
        }
    }

    if (!refreshComplete) {
        Box(contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    val startDestination = when {
        activeSession == null -> "login"
        activeSession?.deviceId.isNullOrBlank() -> "device-setup"
        else -> "home"
    }
    val backStack by navController.currentBackStackEntryAsState()
    val route = backStack?.destination?.route ?: startDestination
    val rootRoute = route.substringBefore('/')
    val primaryRoutes = PrimaryDestinations.map { it.route }.toSet()
    val showBottomBar = !activeSession?.deviceId.isNullOrBlank() && rootRoute in primaryRoutes
    val canGoBack = navController.previousBackStackEntry != null && rootRoute !in primaryRoutes && rootRoute != "login" && rootRoute != "device-setup"
    val title = when (rootRoute) {
        "settings" -> strings.text("settings")
        "updates" -> strings.text("updates")
        "help" -> strings.text("help")
        "about" -> strings.text("about")
        "games" -> strings.text("games")
        "security", "device-details" -> strings.text("security")
        "activity" -> strings.text("activity")
        else -> strings.text("app_name")
    }

    Column {
        if (diagnostics.isForensicTest()) {
            Row(
                modifier = Modifier.fillMaxWidth().background(Color(0xFF7A1F1F)).padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    strings.text("physical_banner", BuildConfig.VERSION_NAME, BuildConfig.SENTINEL_SOURCE_SHA.take(12)),
                    color = Color.White,
                    modifier = Modifier.weight(1f),
                )
                Button(onClick = {
                    diagnostics.info("QUALITY", "FORENSIC_EXPORT_REQUESTED", details = mapOf("surface" to "global-banner"))
                    diagnostics.exportShare(activity)
                }) { Text(strings.text("export_logs")) }
            }
        }

        Scaffold(
            modifier = Modifier.weight(1f),
            containerColor = MaterialTheme.colorScheme.background,
            topBar = {
                SentinelTopBar(
                    title = title,
                    canGoBack = canGoBack,
                    onBack = { navController.popBackStack() },
                    onNavigate = { destination -> navController.navigate(destination) { launchSingleTop = true } },
                )
            },
            bottomBar = {
                if (showBottomBar) {
                    SentinelBottomBar(rootRoute) { destination ->
                        navController.navigate(destination) {
                            launchSingleTop = true
                            popUpTo("home") { saveState = true }
                            restoreState = true
                        }
                    }
                }
            },
        ) { padding ->
            NavHost(
                navController = navController,
                startDestination = startDestination,
                modifier = Modifier.padding(padding),
                enterTransition = { fadeIn(animationSpec = tween(150)) },
                exitTransition = { fadeOut(animationSpec = tween(150)) },
                popEnterTransition = { fadeIn(animationSpec = tween(150)) },
                popExitTransition = { fadeOut(animationSpec = tween(150)) },
            ) {
                composable("login") {
                    LoginScreen(authApi) { authenticated ->
                        sessionStore.save(activity, authenticated.accessToken, authenticated.refreshToken)
                        activeSession = sessionStore.load(activity)
                        diagnostics.info("AUTH", "LOGIN_SUCCESS", "SUCCESS")
                        navController.navigate("device-setup") { popUpTo("login") { inclusive = true } }
                    }
                }
                composable("device-setup") {
                    val current = activeSession ?: sessionStore.load(activity)
                    if (current == null) {
                        LaunchedEffect(Unit) {
                            navController.navigate("login") { popUpTo("device-setup") { inclusive = true } }
                        }
                    } else {
                        DeviceSetupScreen(current.accessToken, deviceIdentity, deviceApi) { proven ->
                            sessionStore.save(activity, proven.accessToken, proven.refreshToken, proven.deviceId)
                            activeSession = sessionStore.load(activity)
                            diagnostics.info("DEVICE", "PROOF_SUCCESS", "SUCCESS")
                            navController.navigate("home") { popUpTo("device-setup") { inclusive = true } }
                        }
                    }
                }
                composable("home") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        DashboardScreen(
                            current.accessToken,
                            current.deviceId!!,
                            dashboardApi,
                            onDeviceClick = { navController.navigate("device-details") },
                            onGameClick = { navController.navigate("game-details/$it") },
                            onReportProblem = { navController.navigate("quality-report") },
                            onSignedOut = {
                                sessionStore.clear(activity)
                                activeSession = null
                                navController.navigate("login") { popUpTo(navController.graph.id) { inclusive = true } }
                            },
                        )
                    }
                }
                composable("games") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        GamesScreen(current.accessToken, dashboardApi) { navController.navigate("game-details/$it") }
                    }
                }
                composable("security") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        DeviceDetailsContent(current, dashboardApi, deviceIdentity, sessionStore, activity, navController) {
                            activeSession = it
                        }
                    }
                }
                composable("activity") { ActivityScreen(activeSession?.deviceId) }
                composable("device-details") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        DeviceDetailsContent(current, dashboardApi, deviceIdentity, sessionStore, activity, navController) {
                            activeSession = it
                        }
                    }
                }
                composable(
                    "game-details/{entitlementId}",
                    arguments = listOf(navArgument("entitlementId") { type = NavType.StringType }),
                ) { entry ->
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        entry.arguments?.getString("entitlementId")?.let {
                            GameDetailsScreen(current.accessToken, it, dashboardApi)
                        }
                    }
                }
                composable("quality-report") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        QualityReportScreen(current.accessToken, qualityReportApi, diagnostics) { navController.popBackStack() }
                    }
                }
                composable("settings") { SettingsScreen(language, theme, onLanguage, onTheme) }
                composable("updates") { UpdateScreen() }
                composable("help") { HelpScreen() }
                composable("about") { AboutScreen() }
            }
        }
    }
}

@Composable
private fun AuthenticatedRoute(
    session: SecureSessionStore.Companion.Session?,
    store: SecureSessionStore,
    activity: ComponentActivity,
    navController: androidx.navigation.NavHostController,
    content: @Composable (SecureSessionStore.Companion.Session) -> Unit,
) {
    val current = session ?: store.load(activity)
    if (current == null || current.deviceId.isNullOrBlank()) {
        LaunchedEffect(Unit) {
            navController.navigate(if (current == null) "login" else "device-setup") {
                popUpTo(navController.graph.id) { inclusive = true }
            }
        }
    } else {
        content(current)
    }
}

@Composable
private fun DeviceDetailsContent(
    session: SecureSessionStore.Companion.Session,
    api: DashboardApi,
    identity: DeviceIdentity,
    store: SecureSessionStore,
    activity: ComponentActivity,
    navController: androidx.navigation.NavHostController,
    onSessionChanged: (SecureSessionStore.Companion.Session?) -> Unit,
) {
    DeviceDetailsScreen(
        accessToken = session.accessToken,
        deviceId = session.deviceId!!,
        api = api,
        deviceIdentity = identity,
        onRevoked = {
            store.clear(activity)
            onSessionChanged(null)
            navController.navigate("login") { popUpTo(navController.graph.id) { inclusive = true } }
        },
        onRotated = { rotated ->
            val deviceId = rotated.deviceId
            val access = rotated.sessionToken
            val refresh = rotated.refreshToken
            if (!deviceId.isNullOrBlank() && !access.isNullOrBlank() && !refresh.isNullOrBlank()) {
                store.save(activity, access, refresh, deviceId)
                onSessionChanged(store.load(activity))
                navController.navigate("home") { popUpTo("home") { inclusive = true } }
            }
        },
    )
}
