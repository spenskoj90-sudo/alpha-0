#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "design" / "reference" / "lovable"


class LovableDesignReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((REF / "manifest.json").read_text(encoding="utf-8"))
        cls.tokens = json.loads((REF / "tokens.json").read_text(encoding="utf-8"))
        cls.components = json.loads((REF / "components.json").read_text(encoding="utf-8"))
        cls.screens = json.loads((REF / "screens.json").read_text(encoding="utf-8"))
        cls.assets = json.loads((REF / "assets.json").read_text(encoding="utf-8"))

    def test_source_identity_and_scope_are_explicit(self) -> None:
        self.assertEqual(self.manifest["sourceRepository"], "spenskoj90-sudo/sentinel-aware-companion")
        self.assertEqual(self.manifest["sourceSha"], "a281479677d84de21a24db62b0b13af7ae11c623")
        self.assertEqual(self.manifest["sourceAgent"], "Lovable")
        self.assertEqual(self.manifest["status"], "REFERENCE_IMPORTED")
        self.assertEqual(self.manifest["nativeAccess"], "NOT_AVAILABLE")
        self.assertEqual(self.manifest["visualAcceptance"], "OWNER_REQUIRED")

    def test_registries_are_complete_and_unique(self) -> None:
        self.assertIn("dark", self.tokens["color"])
        self.assertIn("light", self.tokens["color"])
        self.assertGreaterEqual(len(self.components), 1)
        self.assertEqual(len(self.screens), 92)
        screen_ids = [screen["id"] for screen in self.screens]
        self.assertEqual(len(screen_ids), len(set(screen_ids)))
        self.assertGreaterEqual(len(self.assets["assets"]), 1)
        self.assertIn("nativeOnly", self.assets)

    def test_handoff_and_validator_are_present(self) -> None:
        handoff = (REF / "PRODUCTION-DESIGN-HANDOFF.md").read_text(encoding="utf-8")
        foundations = (REF / "SENTINEL-FOUNDATIONS.md").read_text(encoding="utf-8")
        validator = (REF / "validate-design.mjs").read_text(encoding="utf-8")
        self.assertIn("Native Android/Windows builds", handoff)
        self.assertIn("Microphone never opens", handoff)
        self.assertIn("Intelligence grammar", foundations)
        self.assertIn("scripts/validate-design.mjs", handoff)
        self.assertIn("design/tokens.json", validator)


if __name__ == "__main__":
    unittest.main()
