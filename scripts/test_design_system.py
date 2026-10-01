#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
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
        cls.web_admin = read("web/app/admin/page.tsx")
        cls.web_brand = read("web/app/components/brand-mark.tsx")
        cls.web_intelligence = read("web/app/components/recommendation-panel.tsx")
        cls.site_css = read("site/app/globals.css")
        cls.site_page = read("site/app/page.tsx") + read("site/app/content.tsx")
        cls.site_security = read("site/app/security/page.tsx") + read("site/app/security/content.tsx")
        cls.site_config = read("site/next.config.mjs")
        cls.android = read("app/src/main/java/com/alpha0/app/ui/DesignTokens.kt")
        cls.chrome = read("app/src/main/java/com/alpha0/app/ui/AppChrome.kt")
        cls.main_activity = read("app/src/main/java/com/alpha0/app/MainActivity.kt")
        cls.launcher_fg = read("app/src/main/res/drawable/ic_sentinel_launcher_foreground.xml")
        cls.launcher = read("launcher/index.html")
        cls.launcher_renderer = read("launcher/renderer.js")
        cls.overlay = read("launcher/overlay.html")
        cls.overlay_renderer = read("launcher/overlay-renderer.js")
        cls.web_manifest = read("web/app/manifest.ts")
        cls.packaged_runtime = read("launcher/packaged-runtime.js")

    def test_manifest_identity_and_reference_truth(self) -> None:
        self.assertEqual(self.manifest["schema"], "sentinel.design-system.v3")
        self.assertEqual(self.manifest["revision"], "3.0.0")
        self.assertEqual(self.manifest["status"], "ACTIVE")
        self.assertEqual(self.manifest["direction"], "CALM PRECISION / TRUSTED INTELLIGENCE")
        self.assertEqual(self.manifest["designReference"]["sha"], "a6fc9d4c513dde9d549e5dd70159b1365a76b95c")
        self.assertEqual(self.manifest["predecessor"]["status"], "HISTORICAL_REFERENCE")
        self.assertEqual(
            set(self.manifest["designReference"]["referenceSurfaces"]),
            {"Control plane","Android","Companion","Overlay","Voice","Admin","Access","Billing","Resilience","System"},
        )
        self.assertTrue(self.manifest["platform"]["web"]["adminDistinctShell"])
        self.assertTrue(self.manifest["platform"]["voice"]["explicitConsent"])
        self.assertFalse(self.manifest["platform"]["voice"]["continuousListening"])

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
        self.assertIn("RoundedCornerShape(9.dp)", self.chrome)
        self.assertIn("primary.copy(alpha = 0.12f)", self.chrome)
        self.assertNotIn(".width(if (selected) 24.dp else 12.dp)", self.chrome)
        home_icon = read("app/src/main/res/drawable/ic_domain_home.xml")
        activity_icon = read("app/src/main/res/drawable/ic_domain_activity.xml")
        reduced_glyph = read("design/brand/sentinel-glyph.svg")
        self.assertIn("M3.5,10.5 L12,3.5 L20.5,10.5", home_icon)
        self.assertIn("M3,12 H7 L9.7,6.5", activity_icon)
        self.assertNotIn("M12,3.2 L20,7.1", home_icon)
        self.assertNotIn("M46 18c-7-3.7", reduced_glyph)
        self.assertIn("M43 18.5c-3.2-2.2", reduced_glyph)
        self.assertIn("heightIn(min = 60.dp)", self.chrome)
        self.assertIn("PhysicalTestIdentityStrip", self.chrome)
        self.assertIn("PhysicalTestIdentityStrip(", self.main_activity)
        self.assertIn("SentinelSideRail", self.chrome)
        self.assertIn("compactContext", self.chrome)
        self.assertIn("forensicTest && !isLandscape", self.main_activity)
        self.assertIn("showSideRail = isLandscape && showBottomBar", self.main_activity)
        self.assertNotIn("Color(0xFF7A1F1F)", self.main_activity)
        self.assertIn('@drawable/sentinel_master_icon', self.launcher_fg)
        self.assertNotIn("M32,3 L57,15", self.launcher_fg)
        self.assertEqual(self.manifest["brand"]["master512"]["gitBlobSha"], "e4e4dad49fd9522605e1c1018d175f8ea0973fee")
        self.assertIn("sentinel_master_icon", read("app/src/main/res/values-v31/styles.xml"))

    def test_web_v3_structure_modes_and_intelligence(self) -> None:
        self.assertIn("SENTINEL Design System v3.0", self.web)
        self.assertIn("--radius-card: 8px", self.web)
        self.assertIn("@media (prefers-color-scheme: light)", self.web)
        self.assertIn('[data-theme="light"]', self.web)
        self.assertIn('[data-theme="dark"]', self.web)
        self.assertIn("@media (forced-colors: active)", self.web)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.web)
        self.assertIn("grid-template-columns: 232px", self.web)
        self.assertIn('className="side-nav"', self.web_page)
        self.assertIn('id="main-content"', self.web_page)
        self.assertIn("ELEVATED ACCESS · AUDITED", self.web_admin)
        self.assertIn('role="tablist"', self.web_admin)
        self.assertIn("Catalog", self.web_admin)
        self.assertIn("Entitlements", self.web_admin)
        self.assertIn("Quality", self.web_admin)
        self.assertIn('viewBox="0 0 64 64"', self.web_brand)
        self.assertIn("intelligence-kind", self.web_intelligence)
        self.assertIn("Freshness", self.web_intelligence)
        self.assertIn("UNREPORTED", self.web_intelligence)
        self.assertIn("Source / time", self.web_intelligence)
        self.assertIn("Acknowledgement", self.web_intelligence)
        self.assertNotIn("background-image:", self.web)
        self.assertIn("/brand/icon-192.png", self.web_manifest)
        self.assertIn("/brand/icon-512.png", self.web_manifest)

    def test_production_reduced_assets_match_the_approved_studio_geometry(self) -> None:
        for canonical, copies in (
            ("design/brand/sentinel-glyph.svg", ("web/public/brand/glyph.svg", "site/public/brand/glyph.svg", "launcher/assets/sentinel-glyph.svg")),
            ("design/brand/sentinel-glyph-mono.svg", ("web/public/brand/glyph-mono.svg", "site/public/brand/glyph-mono.svg", "launcher/assets/sentinel-glyph-mono.svg")),
        ):
            for copy in copies:
                with self.subTest(asset=copy):
                    self.assertEqual(read(copy), read(canonical))
        self.assertIn("M43 18.5c-3.2-2.2", self.web_brand)
        self.assertNotIn("M46 18c-7-3.7", self.web_brand)

    def test_rendered_companion_marks_match_the_canonical_glyph(self) -> None:
        canonical = ET.fromstring(read("design/brand/sentinel-glyph.svg"))
        expected_shapes = [(node.tag.split("}")[-1], node.attrib) for node in canonical]
        for surface, css_class in ((self.launcher, "brand-mark"), (self.overlay, "mini-mark")):
            with self.subTest(mark=css_class):
                match = re.search(rf'<svg class="{css_class}".*?</svg>', surface)
                self.assertIsNotNone(match)
                rendered = ET.fromstring(match.group())
                self.assertEqual(rendered.attrib["viewBox"], canonical.attrib["viewBox"])
                self.assertEqual([(node.tag.split("}")[-1], node.attrib) for node in rendered], expected_shapes)

    def test_public_site_v3_and_security_separation(self) -> None:
        self.assertIn("PRE-RELEASE", self.site_page)
        self.assertIn("CALM PRECISION / TRUSTED INTELLIGENCE", self.site_page)
        self.assertIn("/brand/sentinel-master-512.png", self.site_page)
        self.assertIn("No public download is offered yet", self.site_page)
        self.assertIn("@media (prefers-color-scheme: light)", self.site_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.site_css)
        self.assertIn("@media (forced-colors: active)", self.site_css)
        self.assertIn('output: "export"', self.site_config)
        self.assertIn("separate surface from the authenticated Web Control Plane", self.site_security)
        self.assertFalse((ROOT / "site" / "app" / "api").exists())

    def test_companion_v3_and_kill_switch(self) -> None:
        for section in ("Overview","Account","Runtime","Resilience","Host configuration","Games","Adapters","Voice","Overlay","Diagnostics","Updates"):
            self.assertIn(section, self.launcher)
        self.assertIn("STOP / KILL SWITCH", self.launcher)
        self.assertIn("window.confirm(", self.launcher_renderer)
        self.assertIn("HOLD TO TALK", self.launcher)
        self.assertIn("LOCAL-ONLY", self.launcher)
        self.assertIn("OFFLINE", self.launcher)
        self.assertIn("voiceHoldActive", self.launcher_renderer)
        self.assertIn("microphone is not continuously listening", self.launcher.lower())
        self.assertIn("@media(forced-colors:active)", self.launcher)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.launcher)
        for asset in ("assets/sentinel-glyph.svg", "assets/sentinel-glyph-mono.svg", "assets/sentinel-icon-64.png", "assets/sentinel-master-512.png"):
            self.assertIn(asset, self.packaged_runtime)

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
