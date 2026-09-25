from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

import app.core.quality_api as quality
from app.core.quality_api import DiagnosticEvent, DiagnosticSnapshot, QualityClusterUpdate, QualityReportCreate


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _event(**updates) -> DiagnosticEvent:
    values = {
        "ts": NOW,
        "elapsed_ms": 1,
        "sequence": 1,
        "level": "INFO",
        "component": "API",
        "event": "REQUEST_COMPLETE",
        "result": "SUCCESS",
        "details": {"path_id": "health"},
    }
    values.update(updates)
    return DiagnosticEvent(**values)


def _snapshot(event: DiagnosticEvent | None = None) -> DiagnosticSnapshot:
    return DiagnosticSnapshot.model_validate({
        "schema": "sentinel.diagnostic-snapshot.v1",
        "mode": "FORENSIC_TEST",
        "generated_at": NOW,
        "app_version": "1.0.0-rc2",
        "source_sha": "a" * 40,
        "build_type": "physicalTest",
        "session_id": "session-1234",
        "dropped_events": 0,
        "events": [(event or _event()).model_dump()],
    })


@pytest.mark.parametrize(
    ("details", "message"),
    [
        ({f"k{i}": i for i in range(33)}, "too many"),
        ({"": "x"}, "invalid diagnostic detail key"),
        ({"x" * 65: "x"}, "invalid diagnostic detail key"),
        ({"bad key": "x"}, "invalid diagnostic detail key"),
        ({"access_token": "x"}, "sensitive diagnostic detail key"),
        ({"password_hint": "x"}, "sensitive diagnostic detail key"),
        ({"safe": "x" * 1025}, "diagnostic detail value too long"),
    ],
)
def test_diagnostic_details_reject_unbounded_sensitive_or_invalid_fields(details, message) -> None:
    with pytest.raises(ValueError, match=message):
        _event(details=details)


@pytest.mark.parametrize(
    "unsafe",
    [
        "Bearer " + "A" * 48,
        "-----BEGIN " + "PRIVATE KEY-----",
    ],
)
def test_diagnostic_text_rejects_secret_like_material(unsafe: str) -> None:
    with pytest.raises(ValueError, match="appears to contain a secret"):
        _event(exception_msg=unsafe)
    with pytest.raises(ValueError, match="appears to contain a secret"):
        _event(exception_stack=unsafe)


def test_diagnostic_details_accept_safe_primitives_and_exception_text() -> None:
    event = _event(
        details={"count": 1, "ratio": 1.5, "ok": True, "none": None, "safe": "bounded"},
        exception_class="RuntimeError",
        exception_msg="bounded failure",
        exception_stack="frame one\nframe two",
    )
    assert event.details["safe"] == "bounded"


def test_diagnostic_snapshot_size_guard_rejects_oversized_serialized_payload(monkeypatch) -> None:
    monkeypatch.setattr(quality, "MAX_DIAGNOSTIC_BYTES", 100)
    with pytest.raises(ValueError, match="snapshot too large"):
        _snapshot()


def test_quality_report_trims_text_and_enforces_exact_diagnostics_consent() -> None:
    report = QualityReportCreate(category="OTHER", title="  Useful title  ", description="  useful description  ")
    assert report.title == "Useful title"
    assert report.description == "useful description"

    with pytest.raises(ValueError, match="matching consent"):
        QualityReportCreate(category="OTHER", title="Useful title", description="description", diagnostics_consent=True)
    with pytest.raises(ValueError, match="matching consent"):
        QualityReportCreate(
            category="OTHER",
            title="Useful title",
            description="description",
            diagnostics=_snapshot(),
            diagnostics_consent=False,
        )
    accepted = QualityReportCreate(
        category="OTHER",
        title="Useful title",
        description="description",
        diagnostics=_snapshot(),
        diagnostics_consent=True,
    )
    assert accepted.diagnostics is not None


def test_cluster_update_requires_at_least_one_change() -> None:
    with pytest.raises(ValueError, match="requires status or severity"):
        QualityClusterUpdate()
    assert QualityClusterUpdate(status="TRIAGED").status == "TRIAGED"
    assert QualityClusterUpdate(severity="HIGH").severity == "HIGH"


def _report(category="OTHER", *, title="Login button fails", description="Cannot continue after tapping login", event=None):
    return QualityReportCreate(
        category=category,
        title=title,
        description=description,
        diagnostics_consent=event is not None,
        diagnostics=_snapshot(event) if event is not None else None,
    )


def test_issue_identity_prefers_strong_diagnostic_signature_and_is_text_stable() -> None:
    strong = _event(level="ERROR", component="AUTH", event="LOGIN_FAILED", error_code="AUTH_DENIED", result="FAILED")
    report = _report("FUNCTIONALITY", event=strong)
    first = quality._issue_identity(report)
    assert first == quality._issue_identity(report)
    assert first[1] == "DIAGNOSTIC"
    assert first[2] == "HIGH"

    text_report = _report(title="Login fails", description="Login form button remains disabled after valid credentials")
    fingerprint, kind, severity = quality._issue_identity(text_report)
    assert len(fingerprint) == 64
    assert kind == "TEXT"
    assert severity == "MEDIUM"


@pytest.mark.parametrize(
    ("category", "event", "expected"),
    [
        ("OTHER", _event(level="ERROR", event="UNCAUGHT_EXCEPTION", result="FAILED"), "CRITICAL"),
        ("OTHER", _event(level="ERROR", error_code="INTEGRITY_FAILURE", result="FAILED"), "CRITICAL"),
        ("SECURITY_PRIVACY", _event(level="INFO"), "HIGH"),
        ("PERFORMANCE", _event(level="WARN", result="SLOW"), "HIGH"),
        ("FUNCTIONALITY", None, "MEDIUM"),
        ("SECURITY_PRIVACY", None, "MEDIUM"),
        ("DESIGN", None, "LOW"),
        ("OTHER", None, "MEDIUM"),
    ],
)
def test_severity_inference_is_evidence_bound(category, event, expected) -> None:
    payload = _report(category, event=event)
    assert quality._infer_severity(payload, event) == expected


def test_priority_score_is_monotonic_bounded_and_severity_weighted() -> None:
    assert quality._priority_score("LOW", 1, 1) == 15
    assert quality._priority_score("CRITICAL", 1, 1) == 70
    assert quality._priority_score("HIGH", 100000, 100000) == 80
    assert quality._priority_score("CRITICAL", 100000, 100000) == 100


def test_normalized_text_tokens_remove_stop_words_deduplicate_and_bound() -> None:
    tokens = quality._normalized_text_tokens(
        "The sentinel problem LOGIN login button " + " ".join(f"token{i}" for i in range(30))
    )
    assert "the" not in tokens
    assert "sentinel" not in tokens
    assert tokens.count("login") == 1
    assert len(tokens) == 16
    assert tokens == sorted(tokens)


def test_postgres_record_decodes_string_diagnostics_and_preserves_mapping() -> None:
    parsed = quality._postgres_record({
        "id": "report",
        "diagnostics_json": json.dumps({"schema": "sentinel.diagnostic-snapshot.v1"}),
    })
    assert parsed["diagnostics"]["schema"] == "sentinel.diagnostic-snapshot.v1"
    assert "diagnostics_json" not in parsed
    assert quality._postgres_record({"id": "report", "diagnostics_json": {"x": 1}})["diagnostics"] == {"x": 1}
    assert quality._postgres_record({"id": "report"})["diagnostics"] is None


def _record():
    return {
        "id": "report-1",
        "user_id": "user-1",
        "device_id": "device-1",
        "category": "FUNCTIONALITY",
        "title": "Title",
        "description": "Description",
        "status": "RECEIVED",
        "cluster_id": "cluster-1",
        "inferred_severity": "HIGH",
        "cluster_occurrence_count": 2,
        "diagnostics_consent": True,
        "quality_program_opt_in": False,
        "diagnostics": {"safe": True},
        "diagnostics_bytes": 10,
        "diagnostics_expires_at": NOW,
        "created_at": NOW,
        "updated_at": "already-iso",
        "issue_fingerprint": "f" * 64,
    }


def test_public_and_admin_report_projection_controls_private_diagnostics() -> None:
    record = _record()
    public = quality._public_report(record, include_diagnostics=False)
    assert "diagnostics" not in public
    assert public["diagnostics_retained"] is True
    assert public["created_at"].endswith("Z")
    assert public["updated_at"] == "already-iso"
    assert quality._public_report(record, include_diagnostics=True)["diagnostics"] == {"safe": True}

    admin = quality._admin_report(record, include_diagnostics=True)
    assert admin["user_id"] == "user-1"
    assert admin["device_id"] == "device-1"
    assert admin["issue_fingerprint"] == "f" * 64


def test_admin_cluster_projection_handles_reports_alias_and_optional_merge() -> None:
    record = _record()
    cluster = {
        "id": "cluster-1",
        "fingerprint": "f" * 64,
        "signature_kind": "TEXT",
        "category": "FUNCTIONALITY",
        "canonical_title": "Title",
        "severity": "HIGH",
        "severity_locked": False,
        "status": "RECEIVED",
        "priority_score": 54,
        "occurrence_count": 2,
        "affected_user_count": 1,
        "affected_device_count": 1,
        "affected_version_count": 1,
        "first_seen_at": NOW,
        "last_seen_at": NOW,
        "last_app_version": "1.0.0-rc2",
        "last_source_sha": "a" * 40,
        "merged_into_id": None,
        "created_at": NOW,
        "updated_at": NOW,
        "reports": [record],
    }
    simple = quality._admin_cluster(cluster, include_reports=False)
    assert "reports" not in simple
    assert simple["merged_into_id"] is None

    cluster["merged_into_id"] = "cluster-target"
    detailed = quality._admin_cluster(cluster, include_reports=True)
    assert detailed["merged_into_id"] == "cluster-target"
    assert detailed["reports"][0]["id"] == "report-1"
    assert "diagnostics" not in detailed["reports"][0]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (NOW, "2026-09-25T12:00:00Z"),
        ("raw", "raw"),
        (123, "123"),
    ],
)
def test_iso_projection_is_bounded_and_deterministic(value, expected) -> None:
    assert quality._iso(value) == expected


def test_copy_cluster_removes_internal_repository_keys() -> None:
    assert quality._copy_cluster({"id": "x", "_users": {"u"}, "_private": 1}) == {"id": "x"}
