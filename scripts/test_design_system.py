#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "design" / "sentinel-design-system.v1.json"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def normalize_hex(value: str) -> str:
    return value.upper()


class DesignSystemContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.web = read("web/app/globals.css")
        cls.web_page = read("web/app/page.tsx")
        cls.android = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.android_accessibility = read("app/src/main/java/com/alpha0/app/ui/AccessibilitySemantics.kt")
        cls.launcher = read("launcher/index.html")
        cls.overlay = read("launcher/overlay.html")

    def test_manifest_identity_and_figma_anchor(self) -> None:
        self.assertEqual(self.manifest["schema"], "sentinel.design-system.v1")
        self.assertEqual(self.manifest["status"], "ACTIVE")
        figma = self.manifest["figma"]
        self.assertEqual(figma["fileKey"], "vRIHsesWZNMEEEjNJu8TjB")
        self.assertEqual(figma["url"], "https://www.figma.com/design/vRIHsesWZNMEEEjNJu8TjB")
        self.assertIn("00 Foundations", figma["authoredPages"])
        self.assertIn("01 Components", figma["authoredPages"])

    def test_web_semantic_aliases_match_css(self) -> None:
        aliases = self.manifest["surfaces"]["web"]["tokens"]
        css_vars = {
            "background": "--bg",
            "surface": "--panel",
            "surfaceRaised": "--panel-2",
            "border": "--border",
            "primary": "--accent",
            "signal": "--accent-2",
            "danger": "--danger",
            "textPrimary": "--text",
            "textSecondary": "--muted",
            "focus": "--accent-2",
        }
        for role, var in css_vars.items():
            expected = aliases[role].lower()
            self.assertRegex(self.web, rf"{re.escape(var)}\s*:\s*{re.escape(expected)}\s*;", role)
        self.assertIn(":focus-visible { outline: 3px solid var(--accent-2)", self.web)
        self.assertIn("@media (forced-colors: active)", self.web)
        self.assertIn("@media (max-width: 800px)", self.web)
        self.assertIn('className="skip-link"', self.web_page)
        self.assertIn('id="main-content"', self.web_page)
        self.assertIn("SECURITY FIRST / DEFAULT DENY", self.web_page)

    def test_android_semantic_aliases_and_typography_match_compose(self) -> None:
        aliases = self.manifest["surfaces"]["android"]["tokens"]
        kotlin_names = {
            "background": "Background",
            "surface": "Surface",
            "border": "Border",
            "primary": "Primary",
            "signal": "Signal",
            "danger": "Danger",
            "textPrimary": "TextPrimary",
            "textSecondary": "TextSecondary",
        }
        for role, name in kotlin_names.items():
            hex_value = normalize_hex(aliases[role]).removeprefix("#")
            self.assertRegex(self.android, rf"val\s+{name}\s*=\s*Color\(0xFF{hex_value}\)", role)
        typography = self.manifest["surfaces"]["android"]["typography"]
        for family in typography.values():
            self.assertIn(f'GoogleFont("{family}")', self.android)
        self.assertIn("RoundedCornerShape(4.dp)", self.android)
        self.assertIn("RoundedCornerShape(14.dp)", self.android)
        for component in ("StatusBadge", "SentinelCard", "PrimaryButton", "DangerButton"):
            self.assertIn(f"fun {component}(", self.android)

    def test_companion_aliases_and_accessibility_match_launcher(self) -> None:
        aliases = self.manifest["surfaces"]["companion"]["tokens"]
        for role in ("background", "surface", "border", "primary", "danger", "textPrimary", "textSecondary", "focus"):
            self.assertIn(aliases[role].lower(), self.launcher.lower(), role)
        self.assertIn('class="skip-link"', self.launcher)
        self.assertIn('id="main-content"', self.launcher)
        self.assertGreaterEqual(self.launcher.count('aria-live="polite"'), 5)
        self.assertIn("@media(forced-colors:active)", self.launcher)
        self.assertIn("outline:3px solid #4ca3ff", self.launcher)
        self.assertIn("STOP / KILL SWITCH", self.launcher)
        self.assertIn("presentation-only", self.launcher)

    def test_overlay_is_read_only_presentation_surface(self) -> None:
        overlay = self.manifest["surfaces"]["companion"]["overlay"]
        self.assertIn("pointer-events: none", self.overlay)
        self.assertIn('aria-live="polite"', self.overlay)
        self.assertIn("background: rgba(8, 13, 18, .86)", self.overlay)
        self.assertIn("color: #eef3f7", self.overlay)
        self.assertEqual(overlay["pointerEvents"], "none")
        self.assertEqual(overlay["authority"], "presentation-only")

    def test_component_mapping_points_to_real_implementation_anchors(self) -> None:
        components = self.manifest["components"]
        self.assertEqual(components["PrimaryAction"]["android"], "PrimaryButton")
        self.assertEqual(components["Status"]["android"], "StatusBadge")
        self.assertEqual(components["OperationalCard"]["android"], "SentinelCard / Material Card")
        self.assertIn(".btn", self.web)
        self.assertIn(".card", self.web)
        self.assertIn("class=\"btn\"", self.launcher)
        self.assertIn("class=\"status\"", self.launcher)

    def test_accessibility_and_authority_contract_is_explicit(self) -> None:
        access = self.manifest["accessibility"]
        self.assertIn("physicalPreRelease", access)
        self.assertIn("API 35 instrumentation", access["android"])
        self.assertIn("liveRegion", self.android_accessibility)
        self.assertIn("OBSERVATIONAL", self.manifest["authorityStates"])
        self.assertIn("DENIED", self.manifest["authorityStates"])
        self.assertIn("EXTERNAL", self.manifest["authorityStates"])
        principles = set(self.manifest["principles"])
        self.assertIn("default-deny", principles)
        self.assertIn("status is never color-only", principles)
        self.assertIn("physical-device acceptance is a final pre-release gate", principles)


if __name__ == "__main__":
    unittest.main()
