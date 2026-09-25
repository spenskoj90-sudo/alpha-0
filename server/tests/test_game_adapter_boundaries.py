from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.game_adapter import (
    AdapterEvent,
    AdapterIdentity,
    AdapterRegistry,
    Capability,
    CapabilityStatus,
    EvidenceLevel,
    _L3CapabilityAdmission,
    _issue_l3_capability_admission,
    normalize_event,
)


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _identity(*, environment_id: str | None = "env-1") -> AdapterIdentity:
    return AdapterIdentity(
        adapter_id="adapter-1",
        adapter_version="1",
        game_id="wow",
        client_family="classic",
        client_version="3.3.5a",
        server_profile="private",
        environment_id=environment_id,
        capability_profile_version="1",
    )


def _cap(status=CapabilityStatus.AVAILABLE, evidence=EvidenceLevel.L3) -> Capability:
    return Capability(
        status=status,
        evidence_level=evidence,
        source=["exact-environment"],
        updated_at=NOW,
    )


@pytest.mark.parametrize(
    ("status", "evidence"),
    [
        (CapabilityStatus.LIMITED, EvidenceLevel.L3),
        (CapabilityStatus.AVAILABLE, EvidenceLevel.L2),
        (CapabilityStatus.UNVERIFIED, EvidenceLevel.L1),
    ],
)
def test_l3_admission_requires_exact_available_l3_capability(status, evidence) -> None:
    with pytest.raises(ValueError, match="AVAILABLE capability with L3 evidence"):
        _issue_l3_capability_admission(
            adapter_id="adapter-1",
            capability_name="wow.identity",
            capability=_cap(status, evidence),
            environment_id="env-1",
            evidence_id="evidence-1",
            evidence_digest_sha256="a" * 64,
        )


@pytest.mark.parametrize(
    "field",
    ["adapter_id", "capability_name", "environment_id", "evidence_id"],
)
def test_l3_admission_requires_all_identity_fields(field: str) -> None:
    values = {
        "adapter_id": "adapter-1",
        "capability_name": "wow.identity",
        "capability": _cap(),
        "environment_id": "env-1",
        "evidence_id": "evidence-1",
        "evidence_digest_sha256": "a" * 64,
    }
    values[field] = ""
    with pytest.raises(ValueError, match="identity fields are required"):
        _issue_l3_capability_admission(**values)


@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "g" * 64])
def test_l3_admission_requires_lowercase_sha256_digest(digest: str) -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        _issue_l3_capability_admission(
            adapter_id="adapter-1",
            capability_name="wow.identity",
            capability=_cap(),
            environment_id="env-1",
            evidence_id="evidence-1",
            evidence_digest_sha256=digest,
        )


def test_l3_admission_constructor_cannot_be_called_without_internal_authority() -> None:
    with pytest.raises(TypeError, match="exact-environment validator"):
        _L3CapabilityAdmission(
            adapter_id="adapter-1",
            capability_name="wow.identity",
            capability=_cap(),
            environment_id="env-1",
            evidence_id="evidence-1",
            evidence_digest_sha256="a" * 64,
            _authority=object(),
        )


def test_registry_rejects_invalid_l3_admission_shape_adapter_and_environment() -> None:
    registry = AdapterRegistry()
    registry.register(_identity())

    with pytest.raises(ValueError, match="invalid L3 capability admission"):
        registry._admit_l3_capability(object())

    valid = _issue_l3_capability_admission(
        adapter_id="missing",
        capability_name="wow.identity",
        capability=_cap(),
        environment_id="env-1",
        evidence_id="evidence-1",
        evidence_digest_sha256="a" * 64,
    )
    with pytest.raises(KeyError, match="not registered"):
        registry._admit_l3_capability(valid)

    wrong_env = _issue_l3_capability_admission(
        adapter_id="adapter-1",
        capability_name="wow.identity",
        capability=_cap(),
        environment_id="env-2",
        evidence_id="evidence-2",
        evidence_digest_sha256="b" * 64,
    )
    with pytest.raises(ValueError, match="environment does not match"):
        registry._admit_l3_capability(wrong_env)

    no_env = AdapterRegistry()
    no_env.register(_identity(environment_id=None))
    admission = _issue_l3_capability_admission(
        adapter_id="adapter-1",
        capability_name="wow.identity",
        capability=_cap(),
        environment_id="env-1",
        evidence_id="evidence-3",
        evidence_digest_sha256="c" * 64,
    )
    with pytest.raises(ValueError, match="environment does not match"):
        no_env._admit_l3_capability(admission)


def test_registry_admits_valid_l3_and_records_only_real_status_changes() -> None:
    registry = AdapterRegistry()
    registry.register(_identity())
    admission = _issue_l3_capability_admission(
        adapter_id="adapter-1",
        capability_name="wow.identity",
        capability=_cap(),
        environment_id="env-1",
        evidence_id="evidence-1",
        evidence_digest_sha256="a" * 64,
    )
    change = registry._admit_l3_capability(admission)
    assert change is not None
    assert change.previous == CapabilityStatus.UNAVAILABLE
    assert change.current == CapabilityStatus.AVAILABLE
    assert registry.require_usable("adapter-1", "wow.identity").status == CapabilityStatus.AVAILABLE

    # Reapplying the same status is idempotent and does not append change noise.
    assert registry._admit_l3_capability(admission) is None
    assert len(registry.changes()) == 1


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("", "invalid capability name"),
        ("x" * 129, "invalid capability name"),
    ],
)
def test_registry_rejects_invalid_capability_name(name: str, error: str) -> None:
    registry = AdapterRegistry()
    registry.register(_identity())
    with pytest.raises(ValueError, match=error):
        registry.set_capability("adapter-1", name, _cap(CapabilityStatus.LIMITED, EvidenceLevel.L2))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", [""]),
        ("source", ["x" * 129]),
        ("constraints", [""]),
        ("constraints", ["x" * 129]),
    ],
)
def test_capability_metadata_rejects_empty_or_unbounded_entries(field, value) -> None:
    kwargs = {
        "status": CapabilityStatus.LIMITED,
        "evidence_level": EvidenceLevel.L2,
        "source": ["source"],
        "constraints": [],
        "updated_at": NOW,
    }
    kwargs[field] = value
    with pytest.raises(ValidationError, match="metadata entries"):
        Capability(**kwargs)


def test_event_payload_key_length_limit_is_enforced_independently_of_key_count() -> None:
    event = AdapterEvent(
        event_id="event-1",
        schema_version="1",
        occurred_at=NOW,
        sequence=1,
        source={"adapter_id": "adapter-1"},
        event_type="state",
        payload={"x" * 129: 1},
    )
    with pytest.raises(ValueError, match="key exceeds length"):
        normalize_event(event)
