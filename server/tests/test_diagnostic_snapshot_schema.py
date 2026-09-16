from __future__ import annotations

import warnings

from pydantic import ValidationError
import pytest

from app.core.quality_api import DiagnosticSnapshot


def diagnostic_snapshot_payload() -> dict:
    return {
        "schema": "sentinel.diagnostic-snapshot.v1",
        "mode": "PRODUCTION",
        "generated_at": "2026-09-16T19:00:00Z",
        "app_version": "1.0.0",
        "source_sha": "a" * 40,
        "build_type": "release",
        "session_id": "diag-session-alias",
        "dropped_events": 0,
        "events": [
            {
                "ts": "2026-09-16T18:59:59Z",
                "elapsed_ms": 1,
                "sequence": 1,
                "level": "INFO",
                "component": "API",
                "event": "REQUEST_COMPLETE",
                "result": "SUCCESS",
                "details": {"path_id": "health"},
            }
        ],
    }


def test_diagnostic_snapshot_preserves_schema_wire_alias() -> None:
    model = DiagnosticSnapshot.model_validate(diagnostic_snapshot_payload())

    dumped = model.model_dump(mode="json")
    assert dumped["schema"] == "sentinel.diagnostic-snapshot.v1"
    assert "schema_" not in dumped

    schema_properties = DiagnosticSnapshot.model_json_schema()["properties"]
    assert "schema" in schema_properties
    assert "schema_" not in schema_properties


def test_internal_schema_field_name_is_not_accepted_as_wire_input() -> None:
    payload = diagnostic_snapshot_payload()
    payload["schema_"] = payload.pop("schema")

    with pytest.raises(ValidationError):
        DiagnosticSnapshot.model_validate(payload)


def test_model_definition_and_validation_emit_no_schema_shadow_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        DiagnosticSnapshot.model_validate(diagnostic_snapshot_payload())

    shadow_warnings = [item for item in caught if 'Field name "schema"' in str(item.message)]
    assert shadow_warnings == []
