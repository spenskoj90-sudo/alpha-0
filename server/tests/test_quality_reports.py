from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ADMIN_TOKEN", "quality-admin-test-token")

from app.core.quality_api import repository
from app.main import app, store

client = TestClient(app)


def reset_quality_state() -> None:
    if hasattr(store, "devices"):
        store.sessions.clear()
        store.audit.clear()
        store.failures.clear()
    with repository._lock:
        repository._memory.clear()


def user_token(user_id: str = "quality-user") -> str:
    token, _, _, _ = store.issue_session(None, user_id, 3600, 3600)
    return token


def snapshot(*, details: dict | None = None) -> dict:
    return {
        "schema": "sentinel.diagnostic-snapshot.v1",
        "mode": "PRODUCTION",
        "generated_at": "2026-09-15T08:00:00Z",
        "app_version": "1.0.0",
        "source_sha": "a" * 40,
        "build_type": "release",
        "session_id": "diag-session-001",
        "dropped_events": 0,
        "events": [
            {
                "ts": "2026-09-15T07:59:58Z",
                "elapsed_ms": 1234,
                "sequence": 4,
                "level": "WARN",
                "component": "API",
                "event": "REQUEST_COMPLETE",
                "result": "FAILURE",
                "request_id": "012345abcdef",
                "error_code": "HTTP_503",
                "duration_ms": 215,
                "details": details or {"path_id": "quality-report", "network": "validated"},
                "exception_class": None,
                "exception_msg": None,
                "exception_stack": None,
            }
        ],
    }


def report_payload(*, with_diagnostics: bool = True) -> dict:
    payload = {
        "category": "FUNCTIONALITY",
        "title": "Dashboard status did not refresh",
        "description": "The device status stayed stale after reconnecting.",
        "diagnostics_consent": with_diagnostics,
        "quality_program_opt_in": True,
    }
    if with_diagnostics:
        payload["diagnostics"] = snapshot()
    return payload


def test_quality_report_requires_authentication() -> None:
    reset_quality_state()
    response = client.post("/v1/quality/reports", json=report_payload(with_diagnostics=False))
    assert response.status_code in {401, 422}


def test_quality_report_accepts_explicit_diagnostics_consent() -> None:
    reset_quality_state()
    token = user_token()
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=report_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    report = body["report"]
    assert report["status"] == "RECEIVED"
    assert report["diagnostics_consent"] is True
    assert report["quality_program_opt_in"] is True
    assert report["diagnostics_retained"] is True
    assert report["diagnostics_bytes"] > 0
    assert body["diagnostics_retention_days"] == 30


def test_quality_report_can_be_submitted_without_diagnostics() -> None:
    reset_quality_state()
    token = user_token()
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=report_payload(with_diagnostics=False),
    )
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["diagnostics_consent"] is False
    assert report["diagnostics_retained"] is False
    assert report["diagnostics_bytes"] == 0


def test_diagnostics_payload_without_matching_consent_is_rejected() -> None:
    reset_quality_state()
    token = user_token()
    payload = report_payload()
    payload["diagnostics_consent"] = False
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 422


def test_sensitive_diagnostic_detail_key_is_rejected_fail_closed() -> None:
    reset_quality_state()
    token = user_token()
    payload = report_payload()
    payload["diagnostics"] = snapshot(details={"access_token": "must-never-be-stored"})
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 422


def test_secret_like_diagnostic_value_is_rejected_fail_closed() -> None:
    reset_quality_state()
    token = user_token()
    payload = report_payload()
    payload["diagnostics"] = snapshot(details={"safe_key": "Bearer abcdefghijklmnopqrstuvwxyz"})
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 422


def test_user_can_read_own_report_but_not_foreign_report() -> None:
    reset_quality_state()
    token = user_token("owner")
    created = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=report_payload(with_diagnostics=False),
    )
    report_id = created.json()["report"]["id"]

    own = client.get(
        f"/v1/quality/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert own.status_code == 200

    foreign = user_token("other-user")
    denied = client.get(
        f"/v1/quality/reports/{report_id}",
        headers={"Authorization": f"Bearer {foreign}"},
    )
    assert denied.status_code == 404


def test_admin_can_triage_and_read_retained_diagnostics() -> None:
    reset_quality_state()
    token = user_token()
    created = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=report_payload(),
    )
    report_id = created.json()["report"]["id"]
    admin_headers = {"X-Sentinel-Admin-Token": os.environ["SENTINEL_ADMIN_TOKEN"]}

    listing = client.get("/v1/admin/quality/reports", headers=admin_headers)
    assert listing.status_code == 200
    assert any(item["id"] == report_id for item in listing.json()["reports"])

    detail = client.get(f"/v1/admin/quality/reports/{report_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["report"]["diagnostics"]["schema"] == "sentinel.diagnostic-snapshot.v1"

    updated = client.post(
        f"/v1/admin/quality/reports/{report_id}/status",
        headers=admin_headers,
        json={"status": "TRIAGED"},
    )
    assert updated.status_code == 200
    assert updated.json()["report"]["status"] == "TRIAGED"
