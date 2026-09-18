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

    def test_language_and_theme_preferences_are_complete_and_persistent(self) -> None:
        self.assertIn("enum class AppLanguage { SYSTEM, RUSSIAN, ENGLISH }", self.preferences)
        self.assertIn("enum class AppThemeMode { SYSTEM, LIGHT, DARK }", self.preferences)
        self.assertIn("getSharedPreferences", self.preferences)
        self.assertIn("putString(KEY_LANGUAGE", self.preferences)
        self.assertIn("putString(KEY_THEME", self.preferences)
        self.assertIn("SentinelLightColorScheme", self.theme)
        self.assertIn("SentinelDarkColorScheme", self.theme)
        self.assertIn("isSystemInDarkTheme()", self.theme)

    def test_bilingual_contract_covers_critical_navigation(self) -> None:
        required = (
            "settings", "updates", "help", "about", "home", "games", "security", "activity",
            "sign_in", "create_account", "forgot_password", "reset_password", "verify_email",
            "continue_google", "continue_telegram", "continue_vk",
            "device_setup", "bind_device", "theme_light", "theme_dark",
        )
        for key in required:
            self.assertGreaterEqual(self.strings.count(f'"{key}" to '), 2, key)
        self.assertIn('"language_ru" to "Русский"', self.strings)
        login = read("app/src/main/java/com/alpha0/app/auth/LoginScreen.kt")
        self.assertIn("requestPasswordReset", login)
        self.assertIn("confirmPasswordReset", login)
        self.assertIn("confirmEmailVerification", login)
        self.assertIn("verticalScroll(rememberScrollState())", login)

    def test_onboarding_layout_cannot_be_stretched_by_decoration(self) -> None:
        self.assertIn("verticalScroll(rememberScrollState())", self.setup)
        self.assertIn(".matchParentSize()", self.tokens)
        canvas = self.tokens.split("Canvas(", 1)[1]
        self.assertNotIn(".fillMaxSize()", canvas.split(") {", 1)[0])

    def test_update_center_uses_play_update_api_and_monotonic_version(self) -> None:
        self.assertIn("AppUpdateManagerFactory.create", self.update)
        self.assertIn("startUpdateFlowForResult", self.update)
        self.assertIn('implementation("com.google.android.play:app-update:2.1.0")', self.gradle)
        version = re.search(r"versionCode\s*=\s*(\d+)", self.gradle)
        self.assertIsNotNone(version)
        self.assertGreaterEqual(int(version.group(1)), 10007)

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
        self.assertIn("#0D1117", self.launcher)
        self.assertIn("#B356FF", self.launcher)
        self.assertIn("#00E5FF", self.launcher)
        self.assertIn("#F0F6FC", self.launcher)

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
