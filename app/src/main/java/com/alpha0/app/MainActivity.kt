package com.alpha0.app

import android.content.Intent
import android.net.Uri
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
import com.alpha0.app.auth.FederatedAuthCoordinator
import com.alpha0.app.auth.LoginScreen
import com.alpha0.app.auth.SessionManager
import com.alpha0.app.dashboard.ActivityScreen
import com.alpha0.app.dashboard.DashboardApi
import com.alpha0.app.dashboard.DashboardScreen
import com.alpha0.app.dashboard.DeviceDetailsScreen
import com.alpha0.app.dashboard.AccountSecurityDetailScreen
import com.alpha0.app.dashboard.DeviceIdentityDetailScreen
import com.alpha0.app.dashboard.SecurityDetailSection
import com.alpha0.app.dashboard.SecurityHubScreen
import com.alpha0.app.dashboard.SessionsDetailScreen
import com.alpha0.app.dashboard.GameDetailsScreen
import com.alpha0.app.dashboard.GamesScreen
import com.alpha0.app.dashboard.MfaRecoveryCodesScreen
import com.alpha0.app.device.DeviceApi
import com.alpha0.app.device.DeviceSetupScreen
import com.alpha0.app.diagnostics.DiagnosticLogger
import com.alpha0.app.help.AboutScreen
import com.alpha0.app.help.HelpScreen
import com.alpha0.app.net.SessionCredentials
import com.alpha0.app.net.SessionRefreshingHttpTransport
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private val sessionStore = SecureSessionStore()
    private val deviceIdentity = DeviceIdentity()
    private var federatedCallbackUri by mutableStateOf<Uri?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        federatedCallbackUri = validatedFederatedCallback(intent)
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
        val sessionSignals = MutableSharedFlow<Unit>(replay = 1, extraBufferCapacity = 8)
        val rawHttpTransport = UrlConnectionHttpTransport(readTimeoutMs = BuildConfig.SENTINEL_HTTP_READ_TIMEOUT_MS)
        val httpTransport = SessionRefreshingHttpTransport(
            baseUrl = BuildConfig.SENTINEL_API_BASE_URL,
            delegate = rawHttpTransport,
            sessionProvider = {
                sessionStore.load(this)?.let { SessionCredentials(it.accessToken, it.refreshToken) }
            },
            onSessionRefreshed = { refreshed ->
                val current = sessionStore.load(this)
                sessionStore.save(this, refreshed.accessToken, refreshed.refreshToken, current?.deviceId)
                sessionSignals.tryEmit(Unit)
            },
            onSessionInvalidated = {
                sessionStore.clear(this)
                sessionSignals.tryEmit(Unit)
            },
        )
        val authApi = AuthApi(BuildConfig.SENTINEL_API_BASE_URL, httpTransport).also { it.attachDiagnostics(this) }
        val federatedAuth = FederatedAuthCoordinator(
            context = this,
            api = authApi,
            callbackScheme = BuildConfig.SENTINEL_AUTH_CALLBACK_SCHEME,
            vkRedirectUri = BuildConfig.SENTINEL_VK_REDIRECT_URI,
        )
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
                        federatedAuth = federatedAuth,
                        federatedCallbackUri = federatedCallbackUri,
                        onFederatedCallbackConsumed = { federatedCallbackUri = null },
                        sessionManager = sessionManager,
                        sessionSignals = sessionSignals,
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

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        federatedCallbackUri = validatedFederatedCallback(intent)
    }

    private fun validatedFederatedCallback(intent: Intent?): Uri? {
        val uri = intent?.data ?: return null
        val generic = uri.scheme == BuildConfig.SENTINEL_AUTH_CALLBACK_SCHEME &&
            uri.host == "callback"
        val expectedVk = runCatching { Uri.parse(BuildConfig.SENTINEL_VK_REDIRECT_URI) }.getOrNull()
        val vk = expectedVk != null &&
            uri.scheme == expectedVk.scheme &&
            uri.host == expectedVk.host &&
            uri.path == expectedVk.path
        return uri.takeIf { generic || vk }
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
    federatedAuth: FederatedAuthCoordinator,
    federatedCallbackUri: Uri?,
    onFederatedCallbackConsumed: () -> Unit,
    sessionManager: SessionManager,
    sessionSignals: SharedFlow<Unit>,
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
    var pendingMfaRecoveryCodes by remember { mutableStateOf<List<String>?>(null) }

    LaunchedEffect(initialSession?.refreshToken) {
        var rotationBoundaryResolved = false
        val pendingRotation = runCatching { deviceIdentity.pendingRotation() }.getOrNull()
        if (pendingRotation != null) {
            diagnostics.info(
                "KEYSTORE",
                "KEY_ROTATION_RECOVERY_START",
                details = mapOf("fingerprint_prefix" to pendingRotation.fingerprint.take(12)),
            )
            when (
                val recovery = withContext(Dispatchers.IO) {
                    deviceApi.recoverRotation(
                        pendingRotation.publicKeyDerBase64,
                        pendingRotation.fingerprint,
                    )
                }
            ) {
                is DeviceApi.Result.Success -> {
                    rotationBoundaryResolved = true
                    sessionStore.clear(activity)
                    try {
                        deviceIdentity.commitRotation(pendingRotation)
                        when (
                            val proof = withContext(Dispatchers.IO) {
                                deviceApi.prove(
                                    recovery.value.deviceId,
                                    recovery.value.challenge,
                                    deviceIdentity,
                                )
                            }
                        ) {
                            is DeviceApi.ProofResult.Success -> {
                                sessionStore.save(
                                    activity,
                                    proof.value.accessToken,
                                    proof.value.refreshToken,
                                    proof.value.deviceId,
                                )
                                diagnostics.info("KEYSTORE", "KEY_ROTATION_RECOVERY_COMPLETE", "SUCCESS")
                            }
                            is DeviceApi.ProofResult.Failure -> diagnostics.warn(
                                "KEYSTORE",
                                "KEY_ROTATION_RECOVERY_PROOF",
                                "FAILURE",
                                errorCode = proof.message,
                            )
                        }
                    } catch (exception: Exception) {
                        diagnostics.error(
                            "KEYSTORE",
                            "KEY_ROTATION_RECOVERY_COMMIT",
                            "FAILURE",
                            errorCode = exception.javaClass.simpleName,
                            throwable = exception,
                        )
                    }
                    activeSession = sessionStore.load(activity)
                }
                is DeviceApi.Result.Failure -> {
                    if (recovery.message == "DEVICE_ROTATION_NOT_FOUND") {
                        runCatching { deviceIdentity.abortRotation(pendingRotation) }
                            .onFailure {
                                diagnostics.error(
                                    "KEYSTORE",
                                    "KEY_ROTATION_RECOVERY_ABORT",
                                    "FAILURE",
                                    errorCode = it.javaClass.simpleName,
                                    throwable = it,
                                )
                            }
                        diagnostics.info("KEYSTORE", "KEY_ROTATION_RECOVERY_NOT_COMMITTED", "SUCCESS")
                    } else {
                        diagnostics.warn(
                            "KEYSTORE",
                            "KEY_ROTATION_RECOVERY_DEFERRED",
                            "DEGRADED",
                            errorCode = recovery.message,
                        )
                    }
                }
            }
        }

        if (rotationBoundaryResolved) {
            refreshComplete = true
        } else if (initialSession == null) {
            refreshComplete = true
        } else {
            diagnostics.info("SESSION", "REFRESH_START")
            sessionManager.refreshStoredSession(activity)
            activeSession = sessionStore.load(activity)
            refreshComplete = true
            diagnostics.info("SESSION", "REFRESH_COMPLETE", if (activeSession != null) "SUCCESS" else "FAILURE")
        }
    }

    LaunchedEffect(sessionSignals) {
        sessionSignals.collect {
            activeSession = sessionStore.load(activity)
            if (activeSession == null && refreshComplete) {
                pendingMfaRecoveryCodes = null
                navController.navigate("login") {
                    popUpTo(navController.graph.id) { inclusive = true }
                }
            }
        }
    }

    if (!refreshComplete) {
        Box(contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    val startDestination = when {
        activeSession == null -> "login"
        activeSession?.deviceId.isNullOrBlank() -> "device-setup"
        federatedCallbackUri != null -> "security-providers"
        else -> "home"
    }
    val backStack by navController.currentBackStackEntryAsState()
    val route = backStack?.destination?.route ?: startDestination
    val rootRoute = route.substringBefore('/')
    val primaryRoutes = PrimaryDestinations.map { it.route }.toSet()
    val showBottomBar = !activeSession?.deviceId.isNullOrBlank() && rootRoute in primaryRoutes
    val canGoBack = navController.previousBackStackEntry != null &&
        rootRoute !in primaryRoutes &&
        rootRoute != "login" &&
        rootRoute != "device-setup" &&
        rootRoute != "mfa-recovery-codes"
    val title = when (rootRoute) {
        "settings" -> strings.text("settings")
        "updates" -> strings.text("updates")
        "help" -> strings.text("help")
        "about" -> strings.text("about")
        "games" -> strings.text("games")
        "security", "security-account", "security-mfa", "security-recovery", "security-sessions", "security-device", "security-providers", "device-details", "mfa-recovery-codes" -> strings.text("security")
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
                    onNavigate = { destination ->
                        if (rootRoute != "mfa-recovery-codes") {
                            navController.navigate(destination) { launchSingleTop = true }
                        }
                    },
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
                    LoginScreen(
                        api = authApi,
                        federatedAuth = federatedAuth,
                        federatedCallbackUri = federatedCallbackUri,
                        onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                    ) { authenticated ->
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
                            onDeviceClick = { navController.navigate("security-device") },
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
                        SecurityHubScreen(
                            accessToken = current.accessToken,
                            deviceId = current.deviceId!!,
                            api = dashboardApi,
                            authApi = authApi,
                        ) { section ->
                            val route = when (section) {
                                SecurityDetailSection.ACCOUNT -> "security-account"
                                SecurityDetailSection.MFA -> "security-mfa"
                                SecurityDetailSection.RECOVERY -> "security-recovery"
                                SecurityDetailSection.SESSIONS -> "security-sessions"
                                SecurityDetailSection.DEVICE -> "security-device"
                                SecurityDetailSection.PROVIDERS -> "security-providers"
                            }
                            navController.navigate(route)
                        }
                    }
                }
                composable("security-account") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        AccountSecurityDetailScreen(
                            section = SecurityDetailSection.ACCOUNT,
                            accessToken = current.accessToken,
                            authApi = authApi,
                            federatedAuth = federatedAuth,
                            federatedCallbackUri = null,
                            onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                            onMfaEnabled = {},
                            onSessionBoundary = {},
                        )
                    }
                }
                composable("security-mfa") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        AccountSecurityDetailScreen(
                            section = SecurityDetailSection.MFA,
                            accessToken = current.accessToken,
                            authApi = authApi,
                            federatedAuth = federatedAuth,
                            federatedCallbackUri = null,
                            onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                            onMfaEnabled = { codes ->
                                sessionStore.clear(activity)
                                activeSession = null
                                pendingMfaRecoveryCodes = codes
                                navController.navigate("mfa-recovery-codes") { popUpTo(navController.graph.id) { inclusive = true } }
                            },
                            onSessionBoundary = {
                                sessionStore.clear(activity)
                                activeSession = null
                                navController.navigate("login") { popUpTo(navController.graph.id) { inclusive = true } }
                            },
                        )
                    }
                }
                composable("security-recovery") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        AccountSecurityDetailScreen(
                            section = SecurityDetailSection.RECOVERY,
                            accessToken = current.accessToken,
                            authApi = authApi,
                            federatedAuth = federatedAuth,
                            federatedCallbackUri = null,
                            onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                            onMfaEnabled = { codes ->
                                sessionStore.clear(activity)
                                activeSession = null
                                pendingMfaRecoveryCodes = codes
                                navController.navigate("mfa-recovery-codes") { popUpTo(navController.graph.id) { inclusive = true } }
                            },
                            onSessionBoundary = {},
                        )
                    }
                }
                composable("security-sessions") { SessionsDetailScreen() }
                composable("security-providers") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        AccountSecurityDetailScreen(
                            section = SecurityDetailSection.PROVIDERS,
                            accessToken = current.accessToken,
                            authApi = authApi,
                            federatedAuth = federatedAuth,
                            federatedCallbackUri = federatedCallbackUri,
                            onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                            onMfaEnabled = {},
                            onSessionBoundary = {},
                        )
                    }
                }
                composable("security-device") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        DeviceIdentityDetailScreen(
                            accessToken = current.accessToken,
                            deviceId = current.deviceId!!,
                            api = dashboardApi,
                            deviceIdentity = deviceIdentity,
                            onRevoked = {
                                sessionStore.clear(activity)
                                activeSession = null
                                navController.navigate("login") { popUpTo(navController.graph.id) { inclusive = true } }
                            },
                            onRotated = { rotated ->
                                val replacementId = rotated.deviceId
                                val access = rotated.sessionToken
                                val refresh = rotated.refreshToken
                                if (!replacementId.isNullOrBlank() && !access.isNullOrBlank() && !refresh.isNullOrBlank()) {
                                    sessionStore.save(activity, access, refresh, replacementId)
                                    activeSession = sessionStore.load(activity)
                                    navController.navigate("home") { popUpTo("home") { inclusive = true } }
                                }
                            },
                        )
                    }
                }
                composable("mfa-recovery-codes") {
                    val codes = pendingMfaRecoveryCodes
                    if (codes.isNullOrEmpty()) {
                        LaunchedEffect(Unit) {
                            navController.navigate("login") {
                                popUpTo(navController.graph.id) { inclusive = true }
                            }
                        }
                    } else {
                        MfaRecoveryCodesScreen(codes = codes) {
                            pendingMfaRecoveryCodes = null
                            navController.navigate("login") {
                                popUpTo(navController.graph.id) { inclusive = true }
                            }
                        }
                    }
                }
                composable("activity") { ActivityScreen(activeSession?.deviceId) }
                composable("device-details") {
                    AuthenticatedRoute(activeSession, sessionStore, activity, navController) { current ->
                        DeviceDetailsContent(
                            session = current,
                            api = dashboardApi,
                            authApi = authApi,
                            federatedAuth = federatedAuth,
                            federatedCallbackUri = federatedCallbackUri,
                            onFederatedCallbackConsumed = onFederatedCallbackConsumed,
                            identity = deviceIdentity,
                            store = sessionStore,
                            activity = activity,
                            navController = navController,
                            onMfaEnabled = { codes ->
                                sessionStore.clear(activity)
                                activeSession = null
                                pendingMfaRecoveryCodes = codes
                                navController.navigate("mfa-recovery-codes") {
                                    popUpTo(navController.graph.id) { inclusive = true }
                                }
                            },
                        ) {
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
    authApi: AuthApi,
    federatedAuth: FederatedAuthCoordinator,
    federatedCallbackUri: Uri?,
    onFederatedCallbackConsumed: () -> Unit,
    identity: DeviceIdentity,
    store: SecureSessionStore,
    activity: ComponentActivity,
    navController: androidx.navigation.NavHostController,
    onMfaEnabled: (List<String>) -> Unit,
    onSessionChanged: (SecureSessionStore.Companion.Session?) -> Unit,
) {
    DeviceDetailsScreen(
        accessToken = session.accessToken,
        deviceId = session.deviceId!!,
        api = api,
        authApi = authApi,
        federatedAuth = federatedAuth,
        federatedCallbackUri = federatedCallbackUri,
        onFederatedCallbackConsumed = onFederatedCallbackConsumed,
        deviceIdentity = identity,
        onMfaEnabled = onMfaEnabled,
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
