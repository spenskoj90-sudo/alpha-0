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
        cls.account_control = read("web/app/components/account-control.tsx")
        cls.android = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.android_accessibility = read("app/src/main/java/com/alpha0/app/ui/AccessibilitySemantics.kt")
        cls.launcher = read("launcher/index.html")
        cls.launcher_accessibility = read("launcher/accessibility-runtime.js")
        cls.overlay = read("launcher/overlay.html")

    def test_manifest_identity_and_figma_anchor(self) -> None:
        self.assertEqual(self.manifest["schema"], "sentinel.design-system.v1")
        self.assertEqual(self.manifest["status"], "ACTIVE")
        figma = self.manifest["figma"]
        self.assertEqual(figma["fileKey"], "vRIHsesWZNMEEEjNJu8TjB")
        self.assertEqual(figma["url"], "https://www.figma.com/design/vRIHsesWZNMEEEjNJu8TjB")
        self.assertEqual(figma["authoredPages"], ["00 Foundations"])
        self.assertEqual(figma["liveInventoryStatus"], "FOUNDATIONS_ONLY")
        self.assertEqual(figma["foundationPageNodeId"], "0:1")
        self.assertEqual(figma["foundationFrameNodeId"], "1:4")
        self.assertEqual(figma["componentPageStatus"], "UNAUTHORED")

        mappings = self.manifest["figmaMappings"]["foundations"]
        self.assertEqual(mappings["pageNodeId"], "0:1")
        self.assertEqual(mappings["frameNodeId"], "1:4")
        token_mappings = mappings["webAndCompanionColorTokens"]
        self.assertEqual(token_mappings["background"]["swatchNodeId"], "1:9")
        self.assertEqual(token_mappings["background"]["codeAnchor"], "--bg")
        self.assertEqual(token_mappings["primary"]["swatchNodeId"], "1:24")
        self.assertEqual(token_mappings["primary"]["codeAnchor"], "--accent")
        self.assertEqual(token_mappings["signal"]["swatchNodeId"], "1:27")
        self.assertEqual(token_mappings["danger"]["swatchNodeId"], "1:30")
        self.assertEqual(token_mappings["border"]["swatchNodeId"], "1:33")

        for component in self.manifest["components"].values():
            self.assertEqual(component["figma"], "UNAUTHORED")

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

    def test_web_account_accessibility_state_contract(self) -> None:
        self.assertIn('aria-busy={busy}', self.account_control)
        self.assertIn('aria-busy="true"', self.account_control)
        self.assertIn('aria-describedby="password-requirement"', self.account_control)
        self.assertIn('id="password-requirement"', self.account_control)
        self.assertIn("role={messageTone === 'error' ? 'alert' : 'status'}", self.account_control)
        self.assertIn("aria-live={messageTone === 'error' ? 'assertive' : 'polite'}", self.account_control)
        self.assertIn('aria-label={actionLabel}', self.account_control)
        self.assertIn('`Start checkout for ${plan.name}`', self.account_control)
        self.assertIn('`Activate free plan ${plan.name}`', self.account_control)

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
        self.assertIn("RoundedCornerShape(20.dp)", self.android)
        self.assertIn("RoundedCornerShape(16.dp)", self.android)
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
        self.assertIn("outline:3px solid #70dbff", self.launcher)
        self.assertIn("STOP / KILL SWITCH", self.launcher)
        self.assertIn("presentation-only", self.launcher)
        self.assertIn('id="account-panel"', self.launcher)
        self.assertIn('aria-busy="false"', self.launcher)
        self.assertIn('accessibility-runtime.js', self.launcher)
        self.assertIn("classList.contains('err')", self.launcher_accessibility)
        self.assertIn("failed ? 'alert' : 'status'", self.launcher_accessibility)
        self.assertIn("failed ? 'assertive' : 'polite'", self.launcher_accessibility)
        self.assertIn("setAccountBusy(true)", self.launcher_accessibility)
        self.assertIn("setAccountBusy(false)", self.launcher_accessibility)

    def test_overlay_is_read_only_presentation_surface(self) -> None:
        overlay = self.manifest["surfaces"]["companion"]["overlay"]
        self.assertIn("pointer-events: none", self.overlay)
        self.assertIn('aria-live="polite"', self.overlay)
        self.assertIn("background: rgba(7, 18, 31, .88)", self.overlay)
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
        self.assertIn("busy state", access["web"])
        self.assertIn("assertive failure state", access["web"])
        self.assertIn("plan-specific action names", access["web"])
        self.assertIn("busy state", access["companion"])
        self.assertIn("assertive failure state", access["companion"])
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
