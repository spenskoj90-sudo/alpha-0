#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class AndroidProductShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main = read("app/src/main/java/com/alpha0/app/MainActivity.kt")
        cls.preferences = read("app/src/main/java/com/alpha0/app/ui/AppPreferences.kt")
        cls.strings = read("app/src/main/java/com/alpha0/app/ui/AppStrings.kt")
        cls.theme = read("app/src/main/java/com/alpha0/app/ui/SentinelTheme.kt")
        cls.chrome = read("app/src/main/java/com/alpha0/app/ui/AppChrome.kt")
        cls.setup = read("app/src/main/java/com/alpha0/app/device/DeviceSetupScreen.kt")
        cls.battery = read("app/src/main/java/com/alpha0/app/device/BatteryOptimization.kt")
        cls.tokens = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.update = read("app/src/main/java/com/alpha0/app/update/UpdateScreen.kt")
        cls.gradle = read("app/build.gradle.kts")
        cls.manifest = read("app/src/main/AndroidManifest.xml")
        cls.launcher = read("app/src/main/res/mipmap-anydpi/ic_launcher.xml")
        cls.product_screens = read("app/src/main/java/com/alpha0/app/dashboard/ProductScreens.kt")
        cls.security_screens = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        cls.dashboard_api = read("app/src/main/java/com/alpha0/app/dashboard/DashboardApi.kt")

    def test_pre_auth_menu_and_product_routes_exist(self) -> None:
        for route in ("settings", "updates", "help", "about"):
            self.assertIn(f'composable("{route}")', self.main)
            self.assertIn(f'"{route}" to "{route}"', self.chrome)
        for route in ("home", "games", "security", "activity"):
            self.assertIn(f'composable("{route}")', self.main)
            self.assertIn(f'AppDestination("{route}"', self.chrome)
        for route in ("security-account", "security-mfa", "security-recovery", "security-sessions", "security-device", "security-providers"):
            self.assertIn(f'composable("{route}")', self.main)
        self.assertNotIn('composable("device-details")', self.main)

    def test_release_surfaces_are_actionable_not_placeholders(self) -> None:
        self.assertIn(".fillMaxSize()", self.main)
        self.assertIn("R.drawable.sentinel_master_icon", self.main)
        self.assertIn('"/v1/audit"', self.dashboard_api)
        self.assertIn("api.getAudit(accessToken)", self.product_screens)
        self.assertNotIn('strings.text("activity_limited_title")', self.product_screens)
        self.assertIn("requestAccountEmailVerification", self.security_screens)
        self.assertNotIn("authApi.requestEmailVerification(email)", self.security_screens)
        self.assertIn("EMAIL_PROVIDER_UNAVAILABLE", self.security_screens)
        self.assertIn("email_delivery_unavailable", self.security_screens)
        self.assertIn("confirmEmailVerification", self.security_screens)
        self.assertIn("provider_ready_to_link", self.security_screens)
        self.assertIn("provider_not_enabled_here", self.security_screens)
        self.assertIn("fun SentinelLoadingState", self.tokens)
        dashboard = read("app/src/main/java/com/alpha0/app/dashboard/DashboardScreen.kt")
        game_details = read("app/src/main/java/com/alpha0/app/dashboard/GameDetailsScreen.kt")
        for screen in (self.product_screens, self.security_screens, dashboard, game_details):
            self.assertIn("SentinelLoadingState", screen)
            self.assertNotIn("CircularProgressIndicator", screen)

    def test_language_and_theme_preferences_are_complete_and_persistent(self) -> None:
        self.assertIn("enum class AppLanguage { SYSTEM, RUSSIAN, ENGLISH }", self.preferences)
        self.assertIn("enum class AppThemeMode { SYSTEM, LIGHT, DARK }", self.preferences)
        self.assertIn("getSharedPreferences", self.preferences)
        self.assertIn("putString(KEY_LANGUAGE", self.preferences)
        self.assertIn("putString(KEY_THEME", self.preferences)
        self.assertIn("SentinelLightColorScheme", self.theme)
        self.assertIn("SentinelDarkColorScheme", self.theme)
        self.assertIn('GoogleFont("Onest")', self.tokens)
        self.assertNotIn('GoogleFont("Outfit")', self.tokens)
        self.assertIn("isSystemInDarkTheme()", self.theme)

    def test_bilingual_contract_covers_critical_navigation(self) -> None:
        required = (
            "settings", "updates", "help", "about", "home", "games", "security", "activity",
            "sign_in", "create_account", "forgot_password", "reset_password", "verify_email",
            "continue_google", "continue_telegram", "continue_vk",
            "mfa_title", "mfa_code", "verify_mfa", "enable_mfa", "disable_mfa",
            "open_authenticator", "authenticator_unavailable",
            "mfa_recovery_title", "continue_sign_in",
            "device_setup", "bind_device", "theme_light", "theme_dark",
        )
        for key in required:
            self.assertGreaterEqual(self.strings.count(f'"{key}" to '), 2, key)
        self.assertIn('"language_ru" to "Русский"', self.strings)
        login = read("app/src/main/java/com/alpha0/app/auth/LoginScreen.kt")
        self.assertIn("requestPasswordReset", login)
        self.assertIn("confirmPasswordReset", login)
        self.assertIn("confirmEmailVerification", login)
        self.assertIn("requestAccountEmailVerification(session.accessToken)", login)
        self.assertIn('strings.text("verification_pending_delivery")', login)
        self.assertIn("completeMfa", login)
        self.assertIn("AuthMode.MFA", login)
        self.assertIn("verticalScroll(rememberScrollState())", login)
        auth_api = read("app/src/main/java/com/alpha0/app/auth/AuthApi.kt")
        security = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        self.assertIn("/v1/auth/mfa/complete", auth_api)
        self.assertIn("/v1/account/mfa/totp/enroll", auth_api)
        self.assertIn("fun confirmMfa()", security)
        self.assertIn("rotateRecoveryCodes", security)
        self.assertIn("setup.otpauthUri", security)
        self.assertIn('strings.text("open_authenticator")', security)


    def test_device_rotation_is_crash_recoverable(self) -> None:
        identity = read("app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt")
        device_api = read("app/src/main/java/com/alpha0/app/device/DeviceApi.kt")
        device_screen = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        core = read("server/app/main.py")
        store = read("server/app/core/store.py")
        self.assertIn("fun pendingRotation()", identity)
        self.assertIn("PENDING_ALIAS", identity)
        self.assertIn("PENDING_FINGERPRINT", identity)
        self.assertIn('"/v1/devices/recover"', device_api)
        self.assertIn("KEY_ROTATION_RECOVERY_START", self.main)
        self.assertIn("KEY_ROTATION_RECOVERY_REQUIRED", device_screen)
        self.assertIn('def recover_device_rotation(', core)
        self.assertIn("store.rotate_device_identity(", core)
        self.assertIn("def rotate_device_identity(", store)

    def test_runtime_session_refresh_and_mfa_revocation_fail_closed(self) -> None:
        transport = read("app/src/main/java/com/alpha0/app/net/HttpTransport.kt")
        security = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        self.assertIn("class SessionRefreshingHttpTransport", transport)
        self.assertIn('url = "$normalizedBaseUrl/v1/sessions/refresh"', transport)
        self.assertIn("isSessionAuthenticationFailure(first)", transport)
        self.assertIn('code == "INVALID_SESSION"', transport)
        self.assertIn("withRequestId(request)", transport)
        self.assertIn("onSessionInvalidated()", transport)
        self.assertIn("sessionSignals.collect", self.main)
        self.assertIn('navController.navigate("mfa-recovery-codes")', self.main)
        self.assertIn("sessionStore.clear(activity)", self.main)
        self.assertIn("activeSession = null", self.main)
        recovery_screen = read("app/src/main/java/com/alpha0/app/dashboard/MfaRecoveryCodesScreen.kt")
        self.assertIn("fun MfaRecoveryCodesScreen", recovery_screen)
        self.assertIn("onMfaEnabled(result.codes)", security)
        self.assertNotIn("mfaSessionRevoked", security)

    def test_onboarding_layout_has_no_layout_stretching_decoration(self) -> None:
        self.assertIn("verticalScroll(rememberScrollState())", self.setup)
        self.assertNotIn("Canvas(", self.tokens)
        self.assertNotIn("RoundedCornerShape(18.dp)", self.tokens)
        self.assertIn("RoundedCornerShape(8.dp)", self.tokens)
        self.assertIn("Surface(", self.tokens)

    def test_battery_guidance_uses_system_settings_without_direct_exemption_permission(self) -> None:
        self.assertIn("Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS", self.battery)
        self.assertNotIn("Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", self.battery)
        self.assertNotIn("REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", self.manifest)
        self.assertIn("BatteryOptimization.openSettings(context)", self.setup)
        self.assertIn("Settings.ACTION_APPLICATION_DETAILS_SETTINGS", self.setup)

    def test_update_center_uses_play_update_api_and_monotonic_version(self) -> None:
        self.assertIn("AppUpdateManagerFactory.create", self.update)
        self.assertIn("startUpdateFlowForResult", self.update)
        self.assertIn('implementation("com.google.android.play:app-update:2.1.0")', self.gradle)
        version = re.search(r"canonicalVersionCode\s*=\s*(\d+)", self.gradle)
        self.assertIsNotNone(version)
        self.assertGreaterEqual(int(version.group(1)), 10007)
        self.assertIn("SENTINEL_PHYSICAL_TEST_VERSION_CODE", self.gradle)
        self.assertIn("physicalTestVersionCode", self.gradle)

    def test_modern_android_platform_baseline_is_explicit(self) -> None:
        root_gradle = read("build.gradle.kts")
        wrapper = read("gradle/wrapper/gradle-wrapper.properties")
        bootstrap = read("gradlew")
        self.assertIn('id("com.android.application") version "9.4.1"', root_gradle)
        self.assertNotIn('org.jetbrains.kotlin.android', root_gradle)
        self.assertIn('kotlin-gradle-plugin:2.4.20', root_gradle)
        self.assertIn('org.jetbrains.kotlin.plugin.compose") version "2.4.20"', root_gradle)
        self.assertIn("compileSdk = 37", self.gradle)
        self.assertIn("targetSdk = 36", self.gradle)
        self.assertIn("JvmTarget.JVM_17", self.gradle)
        self.assertIn("gradle-9.7.1-bin.zip", wrapper)
        self.assertIn("GRADLE_VERSION=9.7.1", bootstrap)
        self.assertIn("acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a", wrapper)
        self.assertIn("acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a", bootstrap)
        self.assertIn('androidx.compose:compose-bom:2026.09.00', self.gradle)
        self.assertIn('androidx.core:core-ktx:1.19.1', self.gradle)
        self.assertIn('androidx.lifecycle:lifecycle-runtime-compose:2.11.0', self.gradle)
        self.assertIn('androidx.activity:activity-compose:1.13.0', self.gradle)
        self.assertIn('androidx.navigation:navigation-compose:2.10.2', self.gradle)
        self.assertIn('com.google.android.play:integrity:1.6.0', self.gradle)

    def test_federated_auth_uses_credential_manager_pkce_and_isolated_callbacks(self) -> None:
        auth_api = read("app/src/main/java/com/alpha0/app/auth/AuthApi.kt")
        login = read("app/src/main/java/com/alpha0/app/auth/LoginScreen.kt")
        coordinator = read("app/src/main/java/com/alpha0/app/auth/FederatedAuthCoordinator.kt")
        state_store = read("app/src/main/java/com/alpha0/app/auth/FederatedAuthStateStore.kt")
        self.assertIn('implementation("androidx.credentials:credentials:1.6.0")', self.gradle)
        self.assertIn('implementation("com.google.android.libraries.identity.googleid:googleid:1.2.1")', self.gradle)
        self.assertIn("GetGoogleIdOption.Builder()", coordinator)
        self.assertIn(".setNonce(challenge.nonce)", coordinator)
        self.assertIn("MessageDigest.isEqual", coordinator)
        self.assertIn("FederatedAuthStateStore.Pending", coordinator)
        self.assertIn("AndroidKeyStore", state_store)
        self.assertIn("code_verifier", auth_api)
        self.assertIn("continue_google", self.strings)
        self.assertIn("continue_telegram", self.strings)
        self.assertIn("continue_vk", self.strings)
        self.assertIn('android:scheme="${authCallbackScheme}"', self.manifest)
        self.assertIn('android:host="callback"', self.manifest)
        self.assertIn('android:scheme="${vkRedirectScheme}"', self.manifest)
        self.assertIn('android:host="vk.ru"', self.manifest)
        self.assertIn('android:path="/blank.html"', self.manifest)
        self.assertIn('SENTINEL_VK_REDIRECT_URI', self.gradle)
        self.assertIn('vk$vkClientId://vk.ru/blank.html', self.gradle)
        self.assertIn('android:launchMode="singleTask"', self.manifest)
        self.assertIn("completeBrowserCallback", login)
        device_security = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        self.assertIn("completeBrowserLinkCallback", device_security)
        self.assertIn("linkGoogle", device_security)
        self.assertIn("verticalScroll(rememberScrollState())", device_security)
        for scheme in ("com.alpha0.app.auth.dev", "com.alpha0.app.physicaltest.auth", "com.alpha0.app.auth"):
            self.assertIn(scheme, self.gradle)

    def test_launcher_identity_is_explicit_and_branded(self) -> None:
        self.assertIn('android:icon="@mipmap/ic_launcher"', self.manifest)
        self.assertIn('android:roundIcon="@mipmap/ic_launcher"', self.manifest)
        self.assertIn('android:drawable="@color/sentinel_launcher_background"', self.launcher)
        self.assertIn('android:drawable="@drawable/ic_sentinel_launcher_foreground"', self.launcher)
        launcher_fg = read("app/src/main/res/drawable/ic_sentinel_launcher_foreground.xml")
        self.assertIn('@drawable/sentinel_master_icon', launcher_fg)
        self.assertNotIn("M32,3 L57,15", launcher_fg)
        adaptive = read("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml")
        monochrome = read("app/src/main/res/drawable/ic_sentinel_launcher_monochrome.xml")
        self.assertIn('android:drawable="@drawable/ic_sentinel_launcher_monochrome"', adaptive)
        self.assertIn("#FFFFFFFF", monochrome)

    def test_owner_approved_master_brand_is_shared_by_launcher_and_auth(self) -> None:
        login = read("app/src/main/java/com/alpha0/app/auth/LoginScreen.kt")
        launcher_fg = read("app/src/main/res/drawable/ic_sentinel_launcher_foreground.xml")
        self.assertIn("R.drawable.sentinel_master_icon", login)
        self.assertNotIn("R.drawable.ic_sentinel_brand_mark", login)
        self.assertIn('@drawable/sentinel_master_icon', launcher_fg)

    def test_auth_controls_follow_v3_low_radius_contract(self) -> None:
        login = read("app/src/main/java/com/alpha0/app/auth/LoginScreen.kt")
        self.assertNotIn("RoundedCornerShape(12.dp)", login)
        self.assertNotIn("RoundedCornerShape(14.dp)", login)
        self.assertIn("RoundedCornerShape(6.dp)", login)

    def test_forensic_export_handoff_is_uri_safe_and_observable(self) -> None:
        diagnostics = read("app/src/main/java/com/alpha0/app/diagnostics/DiagnosticLogger.kt")
        self.assertIn("ClipData.newUri", diagnostics)
        self.assertIn("Intent.EXTRA_TITLE", diagnostics)
        self.assertIn("Intent.FLAG_GRANT_READ_URI_PERMISSION", diagnostics)
        self.assertIn("FORENSIC_EXPORT_CHOOSER_OPENED", diagnostics)
        self.assertIn("FORENSIC_EXPORT_PREPARE_FAILED", diagnostics)
        self.assertIn("BuildConfig.SENTINEL_SOURCE_SHA", diagnostics)
        self.assertIn("system share sheet", self.strings)
        self.assertIn("системное меню отправки Android", self.strings)

    def test_distribution_channels_keep_play_and_diagnostics_separate(self) -> None:
        self.assertIn('applicationIdSuffix = ".physicaltest"', self.gradle)
        for channel in ("development", "diagnostic", "play"):
            self.assertIn(f'SENTINEL_DISTRIBUTION_CHANNEL", "\\\"{channel}\\\""', self.gradle)
        self.assertIn("BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL", self.update)

    def test_landscape_shell_preserves_vertical_content_budget(self) -> None:
        self.assertIn("Configuration.ORIENTATION_LANDSCAPE", self.main)
        self.assertIn("val showSideRail = isLandscape && showBottomBar", self.main)
        self.assertIn("SentinelSideRail(rootRoute)", self.main)
        self.assertIn("if (showBottomBar && !isLandscape)", self.main)
        self.assertIn("if (forensicTest && !isLandscape)", self.main)
        self.assertIn("compact = isLandscape", self.main)
        self.assertIn("compactContext = landscapePhysicalContext", self.main)
        self.assertIn('"landscape-top-bar"', self.main)
        self.assertIn('"ORIENTATION_STATE"', self.main)
        self.assertIn('"adaptive_side_rail" to showSideRail', self.main)
        self.assertIn("fun SentinelSideRail(", self.chrome)
        self.assertIn(".fillMaxHeight()", self.chrome)
        self.assertIn(".width(72.dp)", self.chrome)
        self.assertIn(".heightIn(min = 48.dp)", self.chrome)
        self.assertIn("compactContext: String? = null", self.chrome)
        self.assertIn("compactActionLabel: String? = null", self.chrome)
        self.assertIn("fun PhysicalTestIdentityStrip(", self.chrome)

    def test_security_status_badges_are_localized_and_single_line(self) -> None:
        design_tokens = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        security_hub = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        dashboard = read("app/src/main/java/com/alpha0/app/dashboard/DashboardScreen.kt")
        self.assertIn("fun SentinelStatus.labelKey(): String", design_tokens)
        self.assertIn("maxLines = 1", design_tokens)
        self.assertIn("TextOverflow.Ellipsis", design_tokens)
        self.assertIn("strings.text(status.labelKey())", security_hub)
        self.assertNotIn("status.name.lowercase()", security_hub)
        self.assertIn("modifier = Modifier.weight(1f)", dashboard)
        self.assertIn("strings.text(status.labelKey())", dashboard)

    def test_release_gate_names_product_shell(self) -> None:
        gates = read("docs/RELEASE_GATES.md")
        self.assertIn("Android product-shell contract", gates)
        self.assertIn("scripts/test_android_product_shell.py", gates)


if __name__ == "__main__":
    unittest.main()
