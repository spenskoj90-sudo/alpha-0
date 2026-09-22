#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "design" / "sentinel-design-system.v2.1.json"

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class DesignSystemContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.web = read("web/app/globals.css")
        cls.web_page = read("web/app/page.tsx")
        cls.android = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.security = read("app/src/main/java/com/alpha0/app/dashboard/SecurityScreensV2.kt")
        cls.launcher = read("launcher/index.html")
        cls.overlay = read("launcher/overlay.html")

    def test_manifest_identity_and_figma_truth(self) -> None:
        self.assertEqual(self.manifest["schema"], "sentinel.design-system.v2.1")
        self.assertEqual(self.manifest["status"], "ACTIVE")
        self.assertEqual(self.manifest["figma"]["fileKey"], "vRIHsesWZNMEEEjNJu8TjB")
        self.assertEqual(self.manifest["figma"]["foundationPageNodeId"], "0:1")
        self.assertEqual(self.manifest["figma"]["foundationFrameNodeId"], "1:4")
        self.assertEqual(self.manifest["figma"]["writeStatus"], "PENDING_CONNECTOR_LIMIT")

    def test_semantic_status_model_is_explicit(self) -> None:
        expected = {"VERIFIED","ACTIVE","PENDING","WARNING","DENIED","REVOKED","FAILED","UNKNOWN","UNAVAILABLE","STOPPED"}
        self.assertEqual(set(self.manifest["semanticStatuses"]), expected)
        self.assertIn("enum class SentinelStatus", self.android)
        for status in expected:
            self.assertIn(status, self.android)
        self.assertNotIn("active: Boolean", self.android)

    def test_android_tokens_typography_and_structure(self) -> None:
        aliases = self.manifest["colors"]["dark"]
        names = {
            "background":"Background","surface":"Surface","surfaceRaised":"SurfaceRaised","surfaceSunken":"SurfaceSunken",
            "border":"Border","borderStrong":"BorderStrong","primary":"Primary","signal":"Signal","success":"Success",
            "warning":"Warning","danger":"Danger","textPrimary":"TextPrimary","textSecondary":"TextSecondary",
            "textTertiary":"TextTertiary","disabled":"Disabled","focus":"Focus",
        }
        for role, name in names.items():
            value = aliases[role].replace("#","").upper()
            self.assertRegex(self.android, rf"val\s+{name}\s*=\s*Color\(0xFF{value}\)")
        for family in ("Onest","Inter","JetBrains Mono"):
            self.assertIn(f'GoogleFont("{family}")', self.android)
        self.assertNotIn('GoogleFont("Outfit")', self.android)
        self.assertIn("RoundedCornerShape(18.dp)", self.android)
        self.assertIn("RoundedCornerShape(12.dp)", self.android)
        for kind in ("SECURITY","DEVICE","OPERATIONAL","RECOMMENDATION"):
            self.assertIn(kind, self.android)
        self.assertIn("SecurityHubScreen", self.security)
        for section in ("ACCOUNT","MFA","RECOVERY","SESSIONS","DEVICE","PROVIDERS"):
            self.assertIn(section, self.security)

    def test_web_is_structural_and_four_mode_responsive(self) -> None:
        for role, var in {
            "background":"--bg","surface":"--panel","surfaceRaised":"--panel-2","border":"--border",
            "primary":"--accent","signal":"--accent-2","danger":"--danger","textPrimary":"--text","textSecondary":"--muted"
        }.items():
            self.assertRegex(self.web, rf"{re.escape(var)}\s*:\s*{self.manifest['colors']['dark'][role].lower()}")
        self.assertNotIn("background-image:", self.web)
        for bp in ("1199px","1023px","767px","479px"):
            self.assertIn(bp, self.web)
        self.assertIn('className="side-nav"', self.web_page)
        self.assertIn("Privileged admin utility", self.web_page)
        self.assertIn('id="main-content"', self.web_page)

    def test_companion_architecture_and_overlay_authority(self) -> None:
        for section in ("Overview","Account","Runtime","Host configuration","Games","Voice","Diagnostics"):
            self.assertIn(section, self.launcher)
        self.assertIn("STOP / KILL SWITCH", self.launcher)
        self.assertIn("Presentation only", self.launcher)
        self.assertIn("no autonomous game action", self.launcher)
        self.assertIn("pointer-events:none", self.overlay)
        self.assertIn("Presentation only", self.overlay)
        self.assertIn('aria-live="polite"', self.overlay)

    def test_accessibility_contract_remains_explicit(self) -> None:
        self.assertIn(":focus-visible", self.web)
        self.assertIn("@media (forced-colors: active)", self.web)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.web)
        self.assertIn("@media(forced-colors:active)", self.launcher)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.launcher)
        self.assertTrue(self.manifest["acceptance"]["noColorOnlyStatus"])
        self.assertEqual(self.manifest["acceptance"]["minAndroidTouchDp"], 48)
        self.assertEqual(self.manifest["acceptance"]["webNarrowPx"], 320)

if __name__ == "__main__":
    unittest.main()
