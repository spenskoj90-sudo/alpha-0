from __future__ import annotations

import asyncio
import json
import io
import urllib.error
import urllib.request
from sentinel_bridge import state

def test_project_state_uses_repository_contracts(monkeypatch):
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "a" * 40)
    monkeypatch.setenv("SENTINEL_ENV", "test")
    payload = state.project_state()
    assert payload["sourceSha"] == "a" * 40
    assert payload["environment"] == "test"
    assert payload["version"]
    assert payload["design"]["referenceSha"]
    assert payload["surfaces"]

def test_provider_state_never_returns_values(monkeypatch):
    secret = "sk-test-never-return-this"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setenv("SENTINEL_RESEND_API_KEY", "re_test_secret")
    payload = state.provider_state()
    encoded = json.dumps(payload)
    assert payload["providers"]["openai"]["configured"] is True
    assert payload["providers"]["resend"]["configured"] is True
    assert secret not in encoded
    assert "re_test_secret" not in encoded

def test_provider_state_uses_core_names_but_never_claims_core_enablement(monkeypatch):
    for key in ("SENTINEL_STRIPE_SECRET_KEY", "SENTINEL_POSTHOG_PROJECT_KEY", "SENTINEL_GOOGLE_WEB_CLIENT_ID", "SENTINEL_BREVO_API_KEY"):
        monkeypatch.setenv(key, "private-sentinel-config")
    payload = state.provider_state()
    assert payload["evidenceScope"] == "bridge-runtime-environment"
    for provider in ("stripe", "posthog", "googleOidc", "brevo"):
        assert payload["providers"][provider]["configured"] is True
    assert payload["providerEnablementVerified"] is False
    assert "private-sentinel-config" not in json.dumps(payload)

def test_checklist_cannot_claim_verified_release_readiness(monkeypatch):
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "a" * 40)
    monkeypatch.setattr(state, "_read_json", lambda _: {
        "ownerVisualAcceptanceRequired": True,
        "surfaces": [{"id": "android", "ready": True, "ownerVisualAccepted": True}],
    })
    monkeypatch.setattr(state, "_read_text", lambda _: "")
    payload = state.release_readiness()
    assert payload["releaseReady"] is False
    assert payload["checklistSatisfied"] is True
    assert payload["releaseEvidence"]["status"] == "UNVERIFIED"

def test_malformed_surfaces_are_safe_unverified_summary(monkeypatch):
    monkeypatch.setattr(state, "_read_json", lambda _: {"surfaces": [None, "bad", {}]})
    monkeypatch.setattr(state, "_read_text", lambda _: "")
    assert state.release_readiness()["releaseReady"] is False

def test_engineering_queue_does_not_change_external_acceptance_issue_summary(monkeypatch):
    original = state._read_text
    monkeypatch.setattr(state, "_read_text", lambda path: "## Canonical acceptance queue\n- [ ] **#375 — visual**\n\n## Engineering\n- [ ] **#379 — write adapters**\n" if path == "docs/TASKS.md" else original(path))
    assert state.release_readiness()["activeAcceptanceIssues"] == [375]

def test_release_readiness_fails_closed():
    payload = state.release_readiness()
    assert payload["releaseReady"] is False
    assert payload["activeAcceptanceIssues"]
    assert payload["ownerVisualAcceptance"]["pendingSurfaces"]


def test_release_readiness_requires_owner_visual_acceptance(monkeypatch):
    monkeypatch.setattr(state, "_read_json", lambda _: {
        "ownerVisualAcceptanceRequired": True,
        "surfaces": [{"id": "web", "ready": True, "ownerVisualAccepted": False}],
    })
    monkeypatch.setattr(state, "_read_text", lambda _: "")
    payload = state.release_readiness()
    assert payload["releaseReady"] is False


def test_release_readiness_rejects_empty_contract(monkeypatch):
    monkeypatch.setattr(state, "_read_json", lambda _: {})
    monkeypatch.setattr(state, "_read_text", lambda _: "")
    payload = state.release_readiness()
    assert payload["releaseReady"] is False

def test_design_state_reports_unreconciled_lab():
    payload = state.design_state()
    assert payload["productionPinnedSha"]
    assert payload["productionParityClaimed"] is False

def test_invalid_source_sha_is_not_echoed(monkeypatch):
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "not-a-sha")
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    assert state.project_state()["sourceSha"] == "UNKNOWN"

def test_source_sha_uses_render_commit_fallback(monkeypatch):
    monkeypatch.delenv("SENTINEL_SOURCE_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "b" * 40)
    assert state.project_state()["sourceSha"] == "b" * 40


def test_healthz_uses_render_commit_fallback(monkeypatch):
    from sentinel_bridge import server

    monkeypatch.delenv("SENTINEL_SOURCE_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "c" * 40)
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    response = asyncio.run(server.healthz(None))
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["status"] == "ok"
    assert payload["service"] == "sentinel-control-bridge"
    assert payload["sourceSha"] == "c" * 40


def test_runtime_probe_rejects_non_http_and_credentials_without_network(monkeypatch):
    def should_not_open(*_args, **_kwargs):
        raise AssertionError("Untrusted URL must never be opened")
    monkeypatch.setattr(state.urllib.request, "build_opener", should_not_open)
    for url in ("file:///etc/passwd", "https://user:password@example.com", "https://example.com/?callback=https://elsewhere", "https://[invalid"):
        result = state._probe("core", url, "/healthz")
        assert result == {"name": "core", "configured": True, "status": "INVALID_CONFIGURATION"}
        assert url not in json.dumps(result)


def test_probe_no_follow_redirect_and_no_false_health(monkeypatch):
    class FakeOpener:
        def __init__(self):
            self.calls = []
        def open(self, request, timeout):
            self.calls.append((request.full_url, timeout))
            raise urllib.error.HTTPError(request.full_url, 302, "Moved", {}, io.BytesIO(b""))
    opener = FakeOpener()
    def build_opener(*handlers):
        assert state._NoProbeRedirect in handlers
        return opener
    monkeypatch.setattr(state.urllib.request, "build_opener", build_opener)
    result = state._probe("web", "https://web.example", "/")
    assert result["status"] == "DEGRADED" and result["httpStatus"] == 302
    assert opener.calls == [("https://web.example/", 5.0)]


def test_probe_only_exact_200_is_healthy(monkeypatch):
    class FakeResponse:
        def __init__(self, code):
            self.status = code
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
    class FakeOpener:
        def __init__(self):
            self.code = 200
        def open(self, *_args, **_kwargs):
            return FakeResponse(self.code)
    opener = FakeOpener()
    monkeypatch.setattr(state.urllib.request, "build_opener", lambda *_: opener)
    assert state._probe("core", "https://core.example", "/healthz")["status"] == "HEALTHY"
    opener.code = 204
    assert state._probe("core", "https://core.example", "/healthz")["status"] == "DEGRADED"
    opener.code = 301
    assert state._probe("core", "https://core.example", "/healthz")["status"] == "DEGRADED"


def test_absent_acceptance_queue_never_satisfies_repository_checklist(monkeypatch):
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "a" * 40)
    monkeypatch.setattr(state, "_read_json", lambda _: {
        "ownerVisualAcceptanceRequired": True,
        "surfaces": [{"id": "android", "ready": True, "ownerVisualAccepted": True}],
    })
    monkeypatch.setattr(state, "_read_text", lambda _: "## Engineering queue\n- [x] **#371 done**")
    summary = state.release_readiness()
    assert summary["gateInventoryVerified"] is False
    assert summary["checklistSatisfied"] is False
    assert summary["releaseReady"] is False


def test_closed_github_issue_is_not_equivalent_to_accepted_gate(monkeypatch):
    monkeypatch.setattr(state, "_read_text", lambda _: (
        "## Canonical acceptance queue\n"
        "- [x] **Neon pre-release setup**\n"
        "- [ ] **#314 — physical acceptance**\n"
        "\n## Current engineering queue\n"
        "- [ ] **#381 — optional benchmark**\n"
    ))
    summary = state.release_readiness()
    assert summary["gateInventoryVerified"] is True
    assert summary["activeAcceptanceIssues"] == [314]
    assert summary["repositoryPendingAcceptanceGateRefs"] == [314]
    assert summary["githubIssueStateVerified"] is False
    assert summary["releaseReady"] is False
