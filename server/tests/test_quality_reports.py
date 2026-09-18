from __future__ import annotations

import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("SENTINEL_ADMIN_TOKEN", "quality-admin-test-token")
os.environ.setdefault("SENTINEL_ADMIN_TOTP_SECRET", "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")

from app.core.admin import _decode_totp_secret, _totp_at
from app.core.quality_api import DiagnosticSnapshot, repository
from app.main import app, store

client = TestClient(app)
def admin_headers() -> dict[str, str]:
    secret = os.environ["SENTINEL_ADMIN_TOTP_SECRET"]
    code = _totp_at(_decode_totp_secret(secret), int(time.time() // 30))
    return {
        "X-Sentinel-Admin-Token": os.environ["SENTINEL_ADMIN_TOKEN"],
        "X-Sentinel-Admin-TOTP": code,
    }


def reset_quality_state() -> None:
    if hasattr(store, "devices"):
        store.sessions.clear()
        store.audit.clear()
        store.failures.clear()
    with repository._lock:
        repository._memory.clear()
        repository._memory_clusters.clear()


def user_token(user_id: str = "quality-user") -> str:
    token, _, _, _ = store.issue_session(None, user_id, 3600, 3600)
    return token


def snapshot(*, details: dict | None = None, error_code: str = "HTTP_503") -> dict:
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
                "error_code": error_code,
                "duration_ms": 215,
                "details": details or {"path_id": "quality-report", "network": "validated"},
                "exception_class": None,
                "exception_msg": None,
                "exception_stack": None,
            }
        ],
    }


def test_diagnostic_snapshot_preserves_schema_wire_alias() -> None:
    parsed = DiagnosticSnapshot.model_validate(snapshot())
    assert parsed.schema_name == "sentinel.diagnostic-snapshot.v1"
    dumped = parsed.model_dump(mode="json")
    assert dumped["schema"] == "sentinel.diagnostic-snapshot.v1"
    assert "schema_name" not in dumped


def report_payload(*, with_diagnostics: bool = True, error_code: str = "HTTP_503") -> dict:
    payload = {
        "category": "FUNCTIONALITY",
        "title": "Dashboard status did not refresh",
        "description": "The device status stayed stale after reconnecting.",
        "diagnostics_consent": with_diagnostics,
        "quality_program_opt_in": True,
    }
    if with_diagnostics:
        payload["diagnostics"] = snapshot(error_code=error_code)
    return payload


def submit(user_id: str, payload: dict) -> dict:
    token = user_token(user_id)
    response = client.post(
        "/v1/quality/reports",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    return response.json()["report"]


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
    assert report["problem_group_id"]
    assert report["related_report_count"] == 1
    assert report["inferred_severity"] == "HIGH"
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


def test_identity_like_diagnostic_detail_key_is_rejected_fail_closed() -> None:
    reset_quality_state()
    token = user_token()
    payload = report_payload()
    payload["diagnostics"] = snapshot(details={"device_id_prefix": "abcdef012345"})
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

    listing = client.get("/v1/admin/quality/reports", headers=admin_headers())
    assert listing.status_code == 200
    assert any(item["id"] == report_id for item in listing.json()["reports"])

    detail = client.get(f"/v1/admin/quality/reports/{report_id}", headers=admin_headers())
    assert detail.status_code == 200
    assert detail.json()["report"]["diagnostics"]["schema"] == "sentinel.diagnostic-snapshot.v1"

    updated = client.post(
        f"/v1/admin/quality/reports/{report_id}/status",
        headers=admin_headers(),
        json={"status": "TRIAGED"},
    )
    assert updated.status_code == 200
    assert updated.json()["report"]["status"] == "TRIAGED"


def test_identical_diagnostic_failure_clusters_across_users_and_titles() -> None:
    reset_quality_state()
    first_payload = report_payload()
    second_payload = report_payload()
    second_payload["title"] = "Reconnect leaves dashboard data stale"
    second_payload["description"] = "Different wording, same observed backend failure."

    first = submit("cluster-user-1", first_payload)
    second = submit("cluster-user-2", second_payload)

    assert first["problem_group_id"] == second["problem_group_id"]
    assert second["related_report_count"] == 2

    listing = client.get("/v1/admin/quality/clusters", headers=admin_headers())
    assert listing.status_code == 200
    cluster = next(item for item in listing.json()["clusters"] if item["id"] == second["problem_group_id"])
    assert cluster["signature_kind"] == "DIAGNOSTIC"
    assert cluster["occurrence_count"] == 2
    assert cluster["affected_user_count"] == 2
    assert cluster["affected_version_count"] == 1
    assert cluster["severity"] == "HIGH"
    assert cluster["priority_score"] >= 50


def test_different_diagnostic_error_codes_remain_separate_clusters() -> None:
    reset_quality_state()
    first = submit("error-user-1", report_payload(error_code="HTTP_503"))
    second = submit("error-user-2", report_payload(error_code="HTTP_401"))
    assert first["problem_group_id"] != second["problem_group_id"]


def test_text_only_reports_with_same_normalized_title_cluster_conservatively() -> None:
    reset_quality_state()
    first_payload = report_payload(with_diagnostics=False)
    first_payload["title"] = "Dashboard stale refresh status"
    second_payload = report_payload(with_diagnostics=False)
    second_payload["title"] = "Stale dashboard status refresh"

    first = submit("text-user-1", first_payload)
    second = submit("text-user-2", second_payload)
    assert first["problem_group_id"] == second["problem_group_id"]


def test_cluster_triage_updates_all_member_reports_and_locks_severity() -> None:
    reset_quality_state()
    first = submit("triage-user-1", report_payload())
    second = submit("triage-user-2", report_payload())
    cluster_id = first["problem_group_id"]

    updated = client.post(
        f"/v1/admin/quality/clusters/{cluster_id}",
        headers=admin_headers(),
        json={"status": "IN_PROGRESS", "severity": "CRITICAL"},
    )
    assert updated.status_code == 200
    cluster = updated.json()["cluster"]
    assert cluster["status"] == "IN_PROGRESS"
    assert cluster["severity"] == "CRITICAL"
    assert cluster["severity_locked"] is True

    for report_id in (first["id"], second["id"]):
        detail = client.get(f"/v1/admin/quality/reports/{report_id}", headers=admin_headers())
        assert detail.status_code == 200
        assert detail.json()["report"]["status"] == "IN_PROGRESS"


def test_admin_can_merge_confirmed_related_clusters_without_losing_reports() -> None:
    reset_quality_state()
    first = submit("merge-user-1", report_payload(error_code="HTTP_503"))
    second = submit("merge-user-2", report_payload(error_code="HTTP_502"))
    source = first["problem_group_id"]
    target = second["problem_group_id"]

    merged = client.post(
        f"/v1/admin/quality/clusters/{source}/merge",
        headers=admin_headers(),
        json={"target_cluster_id": target},
    )
    assert merged.status_code == 200
    cluster = merged.json()["cluster"]
    assert cluster["id"] == target
    assert cluster["occurrence_count"] == 2
    assert cluster["affected_user_count"] == 2

    listing = client.get("/v1/admin/quality/clusters", headers=admin_headers())
    ids = {item["id"] for item in listing.json()["clusters"]}
    assert target in ids
    assert source not in ids

    source_report = client.get(f"/v1/admin/quality/reports/{first['id']}", headers=admin_headers())
    assert source_report.status_code == 200
    assert source_report.json()["report"]["problem_group_id"] == target


def test_chained_cluster_merges_flatten_aliases_and_route_future_reports_to_root() -> None:
    reset_quality_state()
    first = submit("chain-user-1", report_payload(error_code="HTTP_503"))
    second = submit("chain-user-2", report_payload(error_code="HTTP_502"))
    third = submit("chain-user-3", report_payload(error_code="HTTP_504"))
    first_id = first["problem_group_id"]
    second_id = second["problem_group_id"]
    root_id = third["problem_group_id"]

    first_merge = client.post(
        f"/v1/admin/quality/clusters/{first_id}/merge",
        headers=admin_headers(),
        json={"target_cluster_id": second_id},
    )
    assert first_merge.status_code == 200
    second_merge = client.post(
        f"/v1/admin/quality/clusters/{second_id}/merge",
        headers=admin_headers(),
        json={"target_cluster_id": root_id},
    )
    assert second_merge.status_code == 200

    routed = submit("chain-user-4", report_payload(error_code="HTTP_503"))
    assert routed["problem_group_id"] == root_id
    assert routed["related_report_count"] == 4

    listing = client.get("/v1/admin/quality/clusters", headers=admin_headers())
    assert listing.status_code == 200
    active_ids = {item["id"] for item in listing.json()["clusters"]}
    assert root_id in active_ids
    assert first_id not in active_ids
    assert second_id not in active_ids

    first_alias = client.get(f"/v1/admin/quality/clusters/{first_id}", headers=admin_headers())
    second_alias = client.get(f"/v1/admin/quality/clusters/{second_id}", headers=admin_headers())
    assert first_alias.status_code == 200
    assert second_alias.status_code == 200
    assert first_alias.json()["cluster"]["merged_into_id"] == root_id
    assert second_alias.json()["cluster"]["merged_into_id"] == root_id

    root = client.get(f"/v1/admin/quality/clusters/{root_id}", headers=admin_headers())
    assert root.status_code == 200
    cluster = root.json()["cluster"]
    assert cluster["occurrence_count"] == 4
    assert cluster["affected_user_count"] == 4
    assert len(cluster["reports"]) == 4


def test_security_privacy_category_alone_cannot_self_promote_to_critical() -> None:
    reset_quality_state()
    payload = report_payload(with_diagnostics=False)
    payload["category"] = "SECURITY_PRIVACY"
    payload["title"] = "Privacy settings wording is confusing"
    payload["description"] = "I want the privacy settings explanation to be clearer."

    report = submit("security-text-user", payload)
    assert report["inferred_severity"] == "MEDIUM"

    cluster = client.get(
        f"/v1/admin/quality/clusters/{report['problem_group_id']}",
        headers=admin_headers(),
    )
    assert cluster.status_code == 200
    assert cluster.json()["cluster"]["severity"] == "MEDIUM"
    assert cluster.json()["cluster"]["priority_score"] < 70


def test_security_privacy_requires_diagnostic_signal_for_critical_inference() -> None:
    reset_quality_state()
    payload = report_payload(error_code="INTEGRITY_FAILURE")
    payload["category"] = "SECURITY_PRIVACY"
    payload["title"] = "Integrity validation failed"
    payload["description"] = "The client recorded an integrity validation failure."

    report = submit("security-signal-user", payload)
    assert report["inferred_severity"] == "CRITICAL"

    cluster = client.get(
        f"/v1/admin/quality/clusters/{report['problem_group_id']}",
        headers=admin_headers(),
    )
    assert cluster.status_code == 200
    assert cluster.json()["cluster"]["severity"] == "CRITICAL"
