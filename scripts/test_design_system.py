#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "design" / "sentinel-design-system.v3.json"

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class DesignSystemContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.web = read("web/app/globals.css")
        cls.web_page = read("web/app/page.tsx")
        cls.web_brand = read("web/app/components/brand-mark.tsx")
        cls.web_intelligence = read("web/app/components/recommendation-panel.tsx")
        cls.android = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.chrome = read("app/src/main/java/com/alpha0/app/ui/AppChrome.kt")
        cls.main_activity = read("app/src/main/java/com/alpha0/app/MainActivity.kt")
        cls.launcher_fg = read("app/src/main/res/drawable/ic_sentinel_launcher_foreground.xml")
        cls.launcher = read("launcher/index.html")
        cls.launcher_renderer = read("launcher/renderer.js")
        cls.overlay = read("launcher/overlay.html")
        cls.overlay_renderer = read("launcher/overlay-renderer.js")

    def test_manifest_identity_and_reference_truth(self) -> None:
        self.assertEqual(self.manifest["schema"], "sentinel.design-system.v3")
        self.assertEqual(self.manifest["revision"], "3.0.0")
        self.assertEqual(self.manifest["status"], "ACTIVE")
        self.assertEqual(self.manifest["direction"], "CALM PRECISION / TRUSTED INTELLIGENCE")
        self.assertEqual(self.manifest["designReference"]["sha"], "60629603299fd8af035c6f05991482cde0363c33")
        self.assertEqual(self.manifest["predecessor"]["status"], "HISTORICAL_REFERENCE")

    def test_contract_has_every_machine_domain(self) -> None:
        required = {
            "colors","semanticRoles","typography","spacing","radii","borders","elevation","opacity",
            "motion","breakpoints","iconSizing","touchTargets","zOrder","dataVisualization",
            "stateGrammar","intelligenceGrammar","platform",
        }
        self.assertTrue(required.issubset(self.manifest))
        self.assertEqual(self.manifest["touchTargets"]["androidDp"], 48)
        self.assertGreaterEqual(self.manifest["touchTargets"]["webPx"], 44)
        self.assertEqual(self.manifest["overlay"]["oneMeaningfulMessage"], True) if "overlay" in self.manifest else None

    def test_semantic_status_and_intelligence_grammar(self) -> None:
        expected = {"VERIFIED","ACTIVE","PENDING","WARNING","DENIED","REVOKED","FAILED","UNKNOWN","UNAVAILABLE","STOPPED"}
        self.assertEqual(set(self.manifest["stateGrammar"]["status"]), expected)
        self.assertIn("enum class SentinelStatus", self.android)
        self.assertIn("enum class SentinelIntelligenceKind", self.android)
        for kind in ("FACT","INFERENCE","RECOMMENDATION"):
            self.assertIn(kind, self.android)
            self.assertIn(kind, self.manifest["intelligenceGrammar"])
        self.assertIn("never healthy/zero", self.manifest["intelligenceGrammar"]["missingOrStale"])

    def test_android_v3_chrome_and_geometry(self) -> None:
        for family in ("Onest","Inter","JetBrains Mono"):
            self.assertIn(f'GoogleFont("{family}")', self.android)
        self.assertIn("SentinelStatus.ACTIVE -> SentinelColors.Signal", self.android)
        self.assertNotIn("RoundedCornerShape(18.dp)", self.android)
        self.assertNotIn("RoundedCornerShape(12.dp)", self.android)
        self.assertIn("RoundedCornerShape(8.dp)", self.android)
        self.assertIn("RoundedCornerShape(6.dp)", self.android)
        self.assertNotIn("NavigationBar(", self.chrome)
        self.assertNotIn("NavigationBarItem(", self.chrome)
        for glyph in ("ic_domain_home","ic_domain_games","ic_domain_security","ic_domain_activity"):
            self.assertIn(glyph, self.chrome)
        self.assertIn("heightIn(min = 60.dp)", self.chrome)
        self.assertIn("PhysicalTestIdentityStrip", self.chrome)
        self.assertIn("PhysicalTestIdentityStrip(", self.main_activity)
        self.assertNotIn("Color(0xFF7A1F1F)", self.main_activity)
        self.assertIn("M32,3 L57,15", self.launcher_fg)

    def test_web_v3_structure_modes_and_intelligence(self) -> None:
        self.assertIn("SENTINEL Design System v3.0", self.web)
        self.assertIn("--radius-card: 8px", self.web)
        self.assertIn("@media (prefers-color-scheme: light)", self.web)
        self.assertIn("@media (forced-colors: active)", self.web)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.web)
        self.assertIn("grid-template-columns: 232px", self.web)
        self.assertIn('className="side-nav"', self.web_page)
        self.assertIn('id="main-content"', self.web_page)
        self.assertIn('viewBox="0 0 64 64"', self.web_brand)
        self.assertIn("intelligence-kind", self.web_intelligence)
        self.assertIn("Freshness", self.web_intelligence)
        self.assertIn("not reported by Core", self.web_intelligence)
        self.assertNotIn("background-image:", self.web)

    def test_companion_v3_and_kill_switch(self) -> None:
        for section in ("Overview","Account","Runtime","Host configuration","Games","Adapters","Voice","Overlay","Diagnostics","Updates"):
            self.assertIn(section, self.launcher)
        self.assertIn("STOP / KILL SWITCH", self.launcher)
        self.assertIn("window.confirm(", self.launcher_renderer)
        self.assertIn("microphone is not continuously listening", self.launcher.lower())
        self.assertIn("@media(forced-colors:active)", self.launcher)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.launcher)

    def test_overlay_is_presentation_only_and_single_message(self) -> None:
        self.assertIn("pointer-events:none", self.overlay)
        self.assertIn("Presentation only", self.overlay)
        self.assertIn('data-density="STANDARD"', self.overlay)
        self.assertIn("MINIMAL", self.overlay_renderer)
        self.assertIn("STANDARD", self.overlay_renderer)
        self.assertIn("EXPANDED", self.overlay_renderer)
        self.assertIn("presentations.at(-1)", self.overlay_renderer)
        self.assertNotIn("slice(-4)", self.overlay_renderer)
        self.assertNotIn("innerHTML", self.overlay_renderer)

if __name__ == "__main__":
    unittest.main()
