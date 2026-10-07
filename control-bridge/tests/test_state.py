from __future__ import annotations

import asyncio
import json
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
