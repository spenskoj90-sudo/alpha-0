#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TelemetryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(read("observability/telemetry-contract.v1.json"))
        cls.gradle = read("app/build.gradle.kts")
        cls.application = read("app/src/main/java/com/alpha0/app/SentinelApplication.kt")
        cls.release_candidate = read(".github/workflows/release-candidate.yml")
        cls.observability = read("docs/OBSERVABILITY.md")
        cls.companion = read("docs/COMPANION_OBSERVABILITY_V1.md")

    def test_contract_identity_and_local_first_policy(self) -> None:
        self.assertEqual(self.contract["schema"], "sentinel.telemetry-contract.v1")
        self.assertEqual(self.contract["status"], "ACTIVE")
        principles = set(self.contract["principles"])
        self.assertIn("local-first", principles)
        self.assertIn("server-minimal", principles)
        self.assertIn("telemetry-never-authorizes-actions", principles)
        self.assertFalse(self.contract["providers"]["posthog"]["enabled"])

    def test_android_build_identity_is_exact_sha_and_allowlisted_environment(self) -> None:
        self.assertIn('providers.environmentVariable("GITHUB_SHA")', self.gradle)
        self.assertIn('Regex("[0-9a-f]{40}")', self.gradle)
        self.assertIn('"release-candidate"', self.gradle)
        self.assertIn('"production"', self.gradle)
        self.assertIn('buildConfigField("String", "SENTINEL_SOURCE_SHA"', self.gradle)
        self.assertIn('buildConfigField("String", "SENTINEL_RUNTIME_ENVIRONMENT"', self.gradle)
        self.assertIn('test "$GITHUB_SHA" = "$SOURCE_SHA"', self.release_candidate)

    def test_sentry_is_fail_closed_without_complete_release_identity(self) -> None:
        required = (
            "dsn.isEmpty() || !SOURCE_SHA.matches(sourceSha) || environment !in ALLOWED_ENVIRONMENTS",
            "options.release = releaseIdentity",
            "options.environment = environment",
            'options.setTag("sentinel.component", "android")',
            'options.setTag("sentinel.source_sha", sourceSha)',
        )
        for value in required:
            self.assertIn(value, self.application)
        self.assertRegex(
            self.application,
            r'com\.alpha0\.app@\$\{BuildConfig\.VERSION_NAME\}\+\$\{BuildConfig\.VERSION_CODE\}\.\$\{sourceSha\.take\(12\)\}',
        )

    def test_sentry_payload_is_minimized_structurally(self) -> None:
        for value in (
            "event.user = null",
            "event.request = null",
            "event.breadcrumbs?.clear()",
            "event::removeExtra",
            "options.isSendDefaultPii = false",
            "options.isAttachScreenshot = false",
            "options.isAttachViewHierarchy = false",
        ):
            self.assertIn(value, self.application)
        self.assertNotIn("User()", self.application)
        self.assertNotIn("SENTRY_DSN =", self.application)

    def test_contract_forbids_sensitive_dimensions_and_separates_ci(self) -> None:
        forbidden = set(self.contract["privacy"]["forbiddenTelemetryDimensions"])
        for required in {"email", "token", "authorization", "session_id", "device_id", "transcript", "audio", "payload"}:
            self.assertIn(required, forbidden)
        github = self.contract["providers"]["githubActions"]
        self.assertTrue(github["mustNotMirrorIntoSentry"])
        self.assertEqual(self.contract["eventClasses"]["ci.failure"]["externalProvider"], "githubActions")

    def test_alerts_and_triage_are_release_correlated_without_fake_provider_evidence(self) -> None:
        alerts = self.contract["alerts"]
        self.assertEqual(alerts["currentReleaseUnhandledFatal"]["severity"], "P1")
        self.assertEqual(alerts["ciRequiredCheckFailure"]["severity"], "blocking")
        self.assertEqual(
            alerts["repeatedSelectedRuntimeError"]["numericProviderThreshold"],
            "external-config-unverified",
        )
        triage = self.contract["triage"]
        self.assertIn("release", triage["dedupeKey"])
        self.assertIn("technical fingerprint", triage["dedupeKey"])
        self.assertTrue(triage["noAutoCloseFromSilence"])

    def test_documentation_preserves_provider_and_evidence_boundaries(self) -> None:
        for text in (
            "exact source SHA",
            "release-candidate",
            "PostHog",
            "GitHub Actions",
            "Linear",
            "P1",
            "physical",
        ):
            self.assertIn(text, self.observability)
        self.assertIn("does not claim PostHog ingestion", self.companion)
        self.assertIn("telemetry", self.companion.lower())

    def test_no_obvious_committed_sentry_dsn(self) -> None:
        # DSN examples must never appear as concrete project endpoints in source/docs.
        for path in (
            "app/build.gradle.kts",
            "app/src/main/java/com/alpha0/app/SentinelApplication.kt",
            "docs/OBSERVABILITY.md",
            "observability/telemetry-contract.v1.json",
        ):
            content = read(path)
            self.assertIsNone(re.search(r"https://[^\s]+@[^\s]+\.ingest\.sentry\.io/\d+", content), path)


if __name__ == "__main__":
    unittest.main()
