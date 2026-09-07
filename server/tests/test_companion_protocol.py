from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.companion_protocol import (
    CompanionEnvelope,
    CompanionHandshake,
    CompanionMessageType,
    CompanionMode,
    CompanionQueue,
    LatencyClass,
    latency_class_for_budget,
    negotiate_handshake,
)


def handshake(**overrides: object) -> CompanionHandshake:
    values = {
        "protocol_version": "1.0",
        "ugs_schema_version": "1.0",
        "adapter_contract_version": "1.0",
        "core_protocol_version": "1.0",
        "capability_profile": "wow.passive.v1",
    }
    values.update(overrides)
    return CompanionHandshake(**values)


def test_compatible_handshake_is_active() -> None:
    result = negotiate_handshake(
        handshake(),
        expected_ugs_schema="1.0",
        expected_adapter_contract="1.0",
        expected_core_protocol="1.0",
        expected_capability_profile="wow.passive.v1",
    )
    assert result.accepted is True
    assert result.reason_code == "HANDSHAKE_ACCEPTED"
    assert result.mode is CompanionMode.ACTIVE


@pytest.mark.parametrize(
    ("field", "expected_value", "expected_reason"),
    [
        ("protocol_version", "1.1", "PROTOCOL_VERSION_UNSUPPORTED"),
        ("ugs_schema_version", "1.1", "UGS_SCHEMA_MISMATCH"),
        ("adapter_contract_version", "1.1", "ADAPTER_CONTRACT_MISMATCH"),
        ("core_protocol_version", "1.1", "CORE_PROTOCOL_MISMATCH"),
        ("capability_profile", "wow.active.v1", "CAPABILITY_PROFILE_MISMATCH"),
    ],
)
def test_handshake_mismatch_fails_closed(
    field: str, expected_value: str, expected_reason: str
) -> None:
    result = negotiate_handshake(
        handshake(**{field: expected_value}),
        expected_ugs_schema="1.0",
        expected_adapter_contract="1.0",
        expected_core_protocol="1.0",
        expected_capability_profile="wow.passive.v1",
    )
    assert result.accepted is False
    assert result.reason_code == expected_reason
    assert result.mode is CompanionMode.STOPPED


def test_handshake_rejects_unknown_fields_and_invalid_version() -> None:
    with pytest.raises(ValidationError):
        handshake(protocol_version="1.x")
    with pytest.raises(ValidationError):
        handshake(extra="unexpected")


def test_envelope_bounds_sequence_and_payload_entries() -> None:
    with pytest.raises(ValidationError):
        CompanionEnvelope(
            sequence=2**63,
            message_type=CompanionMessageType.HEARTBEAT,
            latency_class=LatencyClass.INTERACTIVE,
        )
    with pytest.raises(ValidationError):
        CompanionEnvelope(
            sequence=1,
            message_type=CompanionMessageType.HEARTBEAT,
            latency_class=LatencyClass.INTERACTIVE,
            payload={str(index): index for index in range(65)},
        )


def test_queue_is_bounded_and_reports_backpressure() -> None:
    queue = CompanionQueue(max_items=2)
    for sequence in range(3):
        assert queue.push(
            CompanionEnvelope(
                sequence=sequence,
                message_type=CompanionMessageType.UGS_UPDATE,
                latency_class=LatencyClass.BACKGROUND,
            )
        )

    assert queue.dropped == 1
    assert queue.pop().sequence == 1
    assert queue.pop().sequence == 2
    assert queue.pop() is None


def test_queue_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        CompanionQueue(max_items=0)
    with pytest.raises(ValueError):
        CompanionQueue(max_items=4097)


def test_stopped_queue_rejects_messages_and_clears_buffer() -> None:
    queue = CompanionQueue(max_items=2)
    queue.push(
        CompanionEnvelope(
            sequence=1,
            message_type=CompanionMessageType.HEARTBEAT,
            latency_class=LatencyClass.INTERACTIVE,
        )
    )
    queue.stop()
    assert queue.stopped is True
    assert queue.pop() is None
    assert queue.push(
        CompanionEnvelope(
            sequence=2,
            message_type=CompanionMessageType.HEARTBEAT,
            latency_class=LatencyClass.INTERACTIVE,
        )
    ) is False


def test_latency_classes_have_explicit_budgets() -> None:
    assert latency_class_for_budget(250) is LatencyClass.INTERACTIVE
    assert latency_class_for_budget(251) is LatencyClass.RESPONSIVE
    assert latency_class_for_budget(1000) is LatencyClass.RESPONSIVE
    assert latency_class_for_budget(1001) is LatencyClass.BACKGROUND
    with pytest.raises(ValueError):
        latency_class_for_budget(-1)
