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
            "sign_in", "create_account", "device_setup", "bind_device", "theme_light", "theme_dark",
        )
        for key in required:
            self.assertGreaterEqual(self.strings.count(f'"{key}" to '), 2, key)
        self.assertIn('"language_ru" to "Русский"', self.strings)

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
        self.assertGreaterEqual(int(version.group(1)), 10003)

    def test_release_gate_names_product_shell(self) -> None:
        gates = read("docs/RELEASE_GATES.md")
        self.assertIn("Android product-shell contract", gates)
        self.assertIn("scripts/test_android_product_shell.py", gates)


if __name__ == "__main__":
    unittest.main()
