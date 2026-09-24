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
        cls.tokens = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.update = read("app/src/main/java/com/alpha0/app/update/UpdateScreen.kt")
        cls.gradle = read("app/build.gradle.kts")
        cls.manifest = read("app/src/main/AndroidManifest.xml")
        cls.launcher = read("app/src/main/res/mipmap-anydpi/ic_launcher.xml")

    def test_pre_auth_menu_and_product_routes_exist(self) -> None:
        for route in ("settings", "updates", "help", "about"):
            self.assertIn(f'composable("{route}")', self.main)
            self.assertIn(f'"{route}" to "{route}"', self.chrome)
        for route in ("home", "games", "security", "activity"):
            self.assertIn(f'composable("{route}")', self.main)
            self.assertIn(f'AppDestination("{route}"', self.chrome)
        for route in ("security-account", "security-mfa", "security-recovery", "security-sessions", "security-device", "security-providers"):
            self.assertIn(f'composable("{route}")', self.main)

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
        self.assertIn("completeMfa", login)
        self.assertIn("AuthMode.MFA", login)
        self.assertIn("verticalScroll(rememberScrollState())", login)
        auth_api = read("app/src/main/java/com/alpha0/app/auth/AuthApi.kt")
        security = read("app/src/main/java/com/alpha0/app/dashboard/DeviceDetailsScreen.kt")
        self.assertIn("/v1/auth/mfa/complete", auth_api)
        self.assertIn("/v1/account/mfa/totp/enroll", auth_api)
        self.assertIn("confirmMfaEnrollment", security)
        self.assertIn("rotateRecoveryCodes", security)
        self.assertIn("enrollment.otpauthUri", security)
        self.assertIn('strings.text("open_authenticator")', security)


    def test_device_rotation_is_crash_recoverable(self) -> None:
        identity = read("app/src/main/java/com/alpha0/app/security/DeviceIdentity.kt")
        device_api = read("app/src/main/java/com/alpha0/app/device/DeviceApi.kt")
        device_screen = read("app/src/main/java/com/alpha0/app/dashboard/DeviceDetailsScreen.kt")
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
        security = read("app/src/main/java/com/alpha0/app/dashboard/DeviceDetailsScreen.kt")
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
        self.assertIn("MfaRecoveryCodesScreen", security)
        self.assertIn("onMfaEnabled(result.codes)", security)
        self.assertNotIn("mfaSessionRevoked", security)

    def test_onboarding_layout_has_no_layout_stretching_decoration(self) -> None:
        self.assertIn("verticalScroll(rememberScrollState())", self.setup)
        self.assertNotIn("Canvas(", self.tokens)
        self.assertNotIn("RoundedCornerShape(18.dp)", self.tokens)
        self.assertIn("RoundedCornerShape(8.dp)", self.tokens)
        self.assertIn("Surface(", self.tokens)

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
        self.assertIn('androidx.core:core-ktx:1.19.0', self.gradle)
        self.assertIn('androidx.activity:activity-compose:1.13.0', self.gradle)
        self.assertIn('androidx.navigation:navigation-compose:2.10.1', self.gradle)
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
        device_security = read("app/src/main/java/com/alpha0/app/dashboard/DeviceDetailsScreen.kt")
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

    def test_distribution_channels_keep_play_and_diagnostics_separate(self) -> None:
        self.assertIn('applicationIdSuffix = ".physicaltest"', self.gradle)
        for channel in ("development", "diagnostic", "play"):
            self.assertIn(f'SENTINEL_DISTRIBUTION_CHANNEL", "\\\"{channel}\\\""', self.gradle)
        self.assertIn("BuildConfig.SENTINEL_DISTRIBUTION_CHANNEL", self.update)

    def test_release_gate_names_product_shell(self) -> None:
        gates = read("docs/RELEASE_GATES.md")
        self.assertIn("Android product-shell contract", gates)
        self.assertIn("scripts/test_android_product_shell.py", gates)


if __name__ == "__main__":
    unittest.main()
