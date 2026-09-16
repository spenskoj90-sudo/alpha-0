from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.json_bounds import validate_bounded_json
from app.core.models import BillingWebhookRequest, GameEvent, RecommendationRequest


def test_json_bounds_reject_depth_and_bytes():
    nested = {"a": {"b": {"c": {"d": 1}}}}
    with pytest.raises(ValueError, match="JSON_DEPTH_LIMIT"):
        validate_bounded_json(nested, max_bytes=4096, max_depth=2)
    with pytest.raises(ValueError, match="JSON_BYTE_LIMIT"):
        validate_bounded_json({"value": "x" * 128}, max_bytes=64, max_string_bytes=256)


def test_game_event_payload_is_bounded():
    with pytest.raises(ValidationError):
        GameEvent(
            event_id="event-0001",
            device_id="device-0001",
            type="game.fact",
            schema_version=1,
            occurred_at=datetime.now(UTC),
            sequence=1,
            payload={"blob": "x" * 70_000},
        )


def test_recommendation_and_billing_payloads_are_bounded():
    with pytest.raises(ValidationError):
        RecommendationRequest(context={"blob": "x" * 70_000})
    with pytest.raises(ValidationError):
        BillingWebhookRequest(
            event_id="event-0001",
            provider_subscription_id="sub-test",
            status="ACTIVE",
            occurred_at=datetime.now(UTC),
            payload={"blob": "x" * 140_000},
        )
