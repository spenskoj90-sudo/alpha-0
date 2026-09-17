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
        cls.main_activity = read("app/src/main/java/com/alpha0/app/MainActivity.kt")
        cls.diagnostic_runtime = read("app/src/main/java/com/alpha0/app/diagnostics/DiagnosticRuntime.kt")
        cls.diagnostic_logger = read("app/src/main/java/com/alpha0/app/diagnostics/DiagnosticLogger.kt")
        cls.quality_screen = read("app/src/main/java/com/alpha0/app/quality/QualityReportScreen.kt")
        cls.quality_api = read("server/app/core/quality_api.py")
        cls.posthog = read("server/app/core/posthog_telemetry.py")
        cls.physical_workflow = read(".github/workflows/physical-test-apk.yml")
        cls.release_candidate = read(".github/workflows/release-candidate.yml")
        cls.observability = read("docs/OBSERVABILITY.md")
        cls.companion = read("docs/COMPANION_OBSERVABILITY_V1.md")

    def test_contract_identity_and_local_first_policy(self) -> None:
        self.assertEqual(self.contract["schema"], "sentinel.telemetry-contract.v1")
        self.assertEqual(self.contract["status"], "ACTIVE")
        principles = set(self.contract["principles"])
        self.assertIn("local-first", principles)
        self.assertIn("server-minimal", principles)
        self.assertIn("user-consent-before-diagnostic-upload", principles)
        self.assertIn("physical-test-forensics-never-ship-as-production-mode", principles)
        self.assertIn("telemetry-never-authorizes-actions", principles)
        posthog = self.contract["providers"]["posthog"]
        self.assertFalse(posthog["enabled"])
        self.assertFalse(posthog["enabledByDefault"])
        self.assertEqual(posthog["activationSurface"], "core-companion-staging-only-when-configured")
        self.assertEqual(self.contract["environments"]["providerNetworkAllowlist"], ["staging"])

    def test_android_build_identity_is_exact_sha_and_allowlisted_environment(self) -> None:
        self.assertIn('providers.environmentVariable("GITHUB_SHA")', self.gradle)
        self.assertIn('Regex("[0-9a-f]{40}")', self.gradle)
        self.assertIn('"release-candidate"', self.gradle)
        self.assertIn('"staging"', self.gradle)
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

    def test_posthog_is_staging_only_fail_closed_and_non_person(self) -> None:
        for value in (
            'self.environment != "staging"',
            '"distinct_id": "sentinel-runtime"',
            '"$process_person_profile": False',
            'os.getenv("SENTINEL_POSTHOG_PROJECT_KEY", "")',
            'os.getenv("SENTINEL_RELEASE", "")',
            'os.getenv("SENTINEL_SOURCE_SHA", "")',
            'raise RuntimeError("POSTHOG_NOT_CONFIGURED")',
        ):
            self.assertIn(value, self.posthog)
        allowed = {
            "mode",
            "reason",
            "state",
            "status",
            "outcome",
            "message_type",
            "latency_class",
            "latency_ms",
            "attempt",
            "delay_ms",
            "event_type",
        }
        match = re.search(r"_ALLOWED_ATTRIBUTES = frozenset\(\s*\{(?P<body>.*?)\}\s*\)", self.posthog, re.S)
        self.assertIsNotNone(match)
        keys = set(re.findall(r'"([a-z_]+)"', match.group("body") if match else ""))
        self.assertEqual(keys, allowed)
        self.assertTrue(keys.isdisjoint({"user", "user_id", "session_id", "device_id", "email", "payload", "transcript", "audio"}))

    def test_physical_test_build_is_isolated_from_release(self) -> None:
        local = self.contract["localDiagnostics"]
        physical = local["physicalTest"]
        production = local["production"]
        self.assertEqual(physical["applicationIdSuffix"], ".physicaltest")
        self.assertEqual(physical["mode"], "FORENSIC_TEST")
        self.assertEqual(physical["ringBytes"], 16 * 1024 * 1024)
        self.assertFalse(physical["automaticRemoteUpload"])
        self.assertFalse(physical["sentryEnabled"])
        self.assertEqual(physical["artifactRetentionDays"], 90)
        self.assertEqual(physical["apiEnvironment"], "staging")
        self.assertEqual(physical["apiOrigin"], "https://sentinel-core-staging.onrender.com")
        self.assertEqual(physical["runtimeEnvironment"], "staging")
        self.assertEqual(physical["httpReadTimeoutMs"], 75_000)
        self.assertTrue(physical["coldStartAware"])
        self.assertEqual(physical["artifactManifestSchema"], "sentinel.android-physical-test-artifact.v1")
        self.assertEqual(production["mode"], "PRODUCTION")
        self.assertEqual(production["ringBytes"], 512 * 1024)
        self.assertFalse(production["fullLocalExport"])
        self.assertFalse(production["automaticDiagnosticUpload"])

        for value in (
            'applicationIdSuffix = ".physicaltest"',
            '"SENTINEL_DIAGNOSTICS_MODE", "\\\"FORENSIC_TEST\\\""',
            '"SENTINEL_DIAGNOSTICS_MODE", "\\\"PRODUCTION\\\""',
            '"SENTINEL_DIAGNOSTICS_MAX_BYTES", "16777216"',
            '"SENTINEL_DIAGNOSTICS_MAX_BYTES", "524288"',
            '"SENTINEL_DIAGNOSTICS_EXPORT_ENABLED", "false"',
            '"SENTINEL_HTTP_READ_TIMEOUT_MS", "15000"',
            '"SENTINEL_HTTP_READ_TIMEOUT_MS", "75000"',
        ):
            self.assertIn(value, self.gradle)
        self.assertIn("if (diagnostics.isForensicTest())", self.application)
        self.assertIn("REMOTE_TELEMETRY_DISABLED_FOR_FORENSIC_TEST", self.application)
        self.assertIn("readTimeoutMs = BuildConfig.SENTINEL_HTTP_READ_TIMEOUT_MS", self.main_activity)
        for constructor in ("AuthApi", "DeviceApi", "DashboardApi"):
            self.assertIn(f"{constructor}(BuildConfig.SENTINEL_API_BASE_URL, httpTransport)", self.main_activity)
        self.assertIn("QualityReportApi(BuildConfig.SENTINEL_API_BASE_URL, diag, httpTransport)", self.main_activity)
        self.assertIn('"http_read_timeout_ms" to BuildConfig.SENTINEL_HTTP_READ_TIMEOUT_MS', self.diagnostic_runtime)
        self.assertIn('put("http_read_timeout_ms", BuildConfig.SENTINEL_HTTP_READ_TIMEOUT_MS)', self.diagnostic_logger)

    def test_physical_test_apk_is_exact_sha_built_and_retained(self) -> None:
        self.assertIn("assemblePhysicalTest", self.physical_workflow)
        self.assertIn("PHYSICAL_TEST_SOURCE_SHA: ${{ github.event.pull_request.head.sha || github.sha }}", self.physical_workflow)
        self.assertIn("SENTINEL_SOURCE_SHA: ${{ env.PHYSICAL_TEST_SOURCE_SHA }}", self.physical_workflow)
        self.assertIn("app-physicalTest.apk", self.physical_workflow)
        self.assertIn("testPhysicalTestUnitTest", self.physical_workflow)
        self.assertIn("SENTINEL_RUNTIME_ENVIRONMENT: staging", self.physical_workflow)
        self.assertIn("scripts/physical_test_artifact.py", self.physical_workflow)
        self.assertIn("physical-test-manifest.json", self.physical_workflow)
        self.assertIn("sha256sum", self.physical_workflow)
        self.assertIn("retention-days: 90", self.physical_workflow)
        self.assertNotIn("secrets.", self.physical_workflow)

    def test_user_ticket_diagnostics_require_explicit_consent_and_remain_bounded(self) -> None:
        local = self.contract["localDiagnostics"]
        ticket = local["ticketFlow"]
        production = local["production"]
        self.assertTrue(ticket["snapshotFrozenBeforeReportTextEntry"])
        self.assertTrue(ticket["diagnosticsAttachmentRequiresExplicitConsent"])
        self.assertTrue(ticket["qualityProgramOptInSeparateFromDiagnosticAttachment"])
        self.assertTrue(ticket["ticketCanBeSubmittedWithoutDiagnostics"])
        self.assertFalse(ticket["directPublicIssueCreation"])
        self.assertLessEqual(production["ticketSnapshotMaxBytes"], production["serverSnapshotMaxBytes"])
        self.assertEqual(production["diagnosticRetentionDays"], 30)

        self.assertIn("remember { diagnostics.createTicketSnapshot() }", self.quality_screen)
        self.assertIn("Attach this diagnostic snapshot to my report", self.quality_screen)
        self.assertIn("Contribute this report to SENTINEL quality improvement", self.quality_screen)
        self.assertIn("diagnostics_consent != (self.diagnostics is not None)", self.quality_api)
        self.assertIn("DIAGNOSTIC_RETENTION_DAYS = 30", self.quality_api)
        self.assertIn("MAX_DIAGNOSTIC_BYTES = 384 * 1024", self.quality_api)

    def test_local_diagnostics_explicitly_forbid_high_risk_payloads(self) -> None:
        forbidden = {item.lower() for item in self.contract["localDiagnostics"]["neverCaptureByDefault"]}
        for required in {
            "passwords",
            "access tokens",
            "refresh tokens",
            "session tokens",
            "authorization headers",
            "private keys",
            "raw play integrity tokens",
            "screenshots",
            "raw microphone or audio data",
            "wow savedvariables",
            "game chat or transcripts",
            "arbitrary ticket form text",
        }:
            self.assertIn(required, forbidden)
        self.assertIn("request_body", self.diagnostic_logger)
        self.assertIn("response_body", self.diagnostic_logger)
        self.assertIn("savedvariables", self.diagnostic_logger)
        self.assertIn("microphone_bytes", self.diagnostic_logger)

    def test_contract_forbids_sensitive_external_dimensions_and_separates_ci(self) -> None:
        forbidden = set(self.contract["privacy"]["forbiddenTelemetryDimensions"])
        for required in {"email", "token", "authorization", "session_id", "device_id", "transcript", "audio", "payload"}:
            self.assertIn(required, forbidden)
        github = self.contract["providers"]["githubActions"]
        self.assertTrue(github["mustNotMirrorIntoSentry"])
        self.assertEqual(self.contract["eventClasses"]["ci.failure"]["externalProvider"], "githubActions")
        self.assertEqual(self.contract["eventClasses"]["runtime.operational"]["optionalExternalProvider"], "posthog-staging")

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
        self.assertIn("staging-only PostHog", self.companion)
        self.assertIn("does not claim production PostHog activation", self.companion)
        self.assertIn("telemetry", self.companion.lower())

    def test_no_obvious_committed_sentry_dsn(self) -> None:
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
