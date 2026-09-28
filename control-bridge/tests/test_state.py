from __future__ import annotations

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
    monkeypatch.setenv("RESEND_API_KEY", "re_test_secret")
    payload = state.provider_state()
    encoded = json.dumps(payload)
    assert payload["providers"]["openai"]["configured"] is True
    assert payload["providers"]["resend"]["configured"] is True
    assert secret not in encoded
    assert "re_test_secret" not in encoded

def test_release_readiness_fails_closed():
    payload = state.release_readiness()
    assert payload["releaseReady"] is False
    assert payload["activeAcceptanceIssues"]
    assert payload["ownerVisualAcceptance"]["pendingSurfaces"]

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
