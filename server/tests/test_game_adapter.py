from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.game_adapter import (
    AdapterEvent,
    AdapterIdentity,
    AdapterRegistry,
    Capability,
    CapabilityStatus,
    DataQuality,
    EvidenceLevel,
    normalize_event,
)


NOW = datetime(2026, 9, 6, 15, 0, tzinfo=UTC)


def identity() -> AdapterIdentity:
    return AdapterIdentity(
        adapter_id="wow-retail",
        adapter_version="1.0.0",
        game_id="world-of-warcraft",
        client_family="retail",
        client_version="12.0.x",
        server_profile="official",
        environment_id="test-retail",
        capability_profile_version="1.0",
    )


def capability(status: CapabilityStatus, evidence: EvidenceLevel = EvidenceLevel.L1) -> Capability:
    return Capability(
        status=status,
        evidence_level=evidence,
        source=["game_api"],
        updated_at=NOW,
    )


def test_registry_registers_identity_and_capabilities() -> None:
    registry = AdapterRegistry()
    registry.register(identity())

    change = registry.set_capability("wow-retail", "player.state", capability(CapabilityStatus.LIMITED))

    assert registry.identity("wow-retail").adapter_id == "wow-retail"
    assert registry.capability("wow-retail", "player.state").status == CapabilityStatus.LIMITED
    assert change is not None
    assert change.previous == CapabilityStatus.UNAVAILABLE
    assert change.current == CapabilityStatus.LIMITED


def test_available_requires_l3_evidence() -> None:
    registry = AdapterRegistry()
    registry.register(identity())

    with pytest.raises(ValueError, match="L3 evidence"):
        registry.set_capability("wow-retail", "player.state", capability(CapabilityStatus.AVAILABLE, EvidenceLevel.L2))


def test_l3_available_is_usable() -> None:
    registry = AdapterRegistry()
    registry.register(identity())

    registry.set_capability("wow-retail", "player.state", capability(CapabilityStatus.AVAILABLE, EvidenceLevel.L3))

    assert registry.require_usable("wow-retail", "player.state").is_usable()


def test_capability_can_downgrade() -> None:
    registry = AdapterRegistry()
    registry.register(identity())
    registry.set_capability("wow-retail", "target.state", capability(CapabilityStatus.AVAILABLE, EvidenceLevel.L3))

    change = registry.set_capability("wow-retail", "target.state", capability(CapabilityStatus.UNAVAILABLE))

    assert change.current == CapabilityStatus.UNAVAILABLE
    assert not registry.capability("wow-retail", "target.state").is_usable()
    with pytest.raises(LookupError, match="capability unavailable"):
        registry.require_usable("wow-retail", "target.state")


def test_unregistered_adapter_is_rejected() -> None:
    registry = AdapterRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.set_capability("missing", "player.state", capability(CapabilityStatus.LIMITED))


def test_identical_capability_status_does_not_create_change() -> None:
    registry = AdapterRegistry()
    registry.register(identity())
    registry.set_capability("wow-retail", "combat.state", capability(CapabilityStatus.LIMITED))

    assert registry.set_capability("wow-retail", "combat.state", capability(CapabilityStatus.LIMITED)) is None
    assert len(registry.changes()) == 1


def test_event_requires_non_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        AdapterEvent(
            event_id="e1",
            schema_version="1.0",
            occurred_at=NOW,
            sequence=-1,
            source={"adapter_id": "wow-retail"},
            event_type="player.state.changed",
        )


def test_event_normalization_preserves_semantic_payload() -> None:
    event = AdapterEvent(
        event_id="e1",
        schema_version="1.0",
        occurred_at=NOW,
        sequence=4,
        source={"adapter_id": "wow-retail"},
        event_type="player.state.changed",
        payload={"health": 900, "maximum_health": 1000},
        data_quality=DataQuality.HIGH,
        provenance=["PLAYER_TARGET_CHANGED"],
    )

    normalized = normalize_event(event)
    assert normalized.payload == {"health": 900, "maximum_health": 1000}
    assert normalized.data_quality == DataQuality.HIGH


def test_event_payload_key_limit_is_enforced() -> None:
    event = AdapterEvent(
        event_id="e1",
        schema_version="1.0",
        occurred_at=NOW,
        sequence=1,
        source={"adapter_id": "wow-retail"},
        event_type="player.state.changed",
        payload={str(i): i for i in range(3)},
    )

    with pytest.raises(ValueError, match="key limit"):
        normalize_event(event, max_payload_keys=2)


def test_unknown_capability_is_not_usable() -> None:
    registry = AdapterRegistry()
    registry.register(identity())
    registry.set_capability("wow-retail", "target.health", capability(CapabilityStatus.UNVERIFIED))

    with pytest.raises(LookupError):
        registry.require_usable("wow-retail", "target.health")
