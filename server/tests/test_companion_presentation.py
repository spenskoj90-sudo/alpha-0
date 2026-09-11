from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.companion_interaction import CompanionPresentationChannel
from app.core.companion_presentation import health_presentation, recommendation_presentations
from app.core.companion_protocol import CompanionMode
from app.core.companion_transport import CompanionRuntimeHealth
from app.core.models import Recommendation, RecommendationResponse


def health() -> CompanionRuntimeHealth:
    now = datetime.now(UTC)
    return CompanionRuntimeHealth(
        mode=CompanionMode.ACTIVE,
        last_heartbeat=now,
        last_latency_ms=42.0,
        reconnect_attempts=0,
        queue_depth=1,
        dropped_events=0,
        last_successful_send=now,
        kill_switch_active=False,
        peer_authenticated=True,
        peer_id="peer-1",
    )


def test_health_presentation_is_observational() -> None:
    item = health_presentation(health(), channel=CompanionPresentationChannel.VOICE)
    assert item.channel is CompanionPresentationChannel.VOICE
    assert item.action_capable is False
    assert "ACTIVE" in item.text


def test_recommendation_presentation_preserves_evidence() -> None:
    response = RecommendationResponse(recommendations=[
        Recommendation(
            kind="recommendation",
            text="Review the current state.",
            confidence=0.8,
            provenance=["test"],
            provider_id="sentinel-core",
            model_id="context-baseline-v1",
        )
    ])
    items = recommendation_presentations(response)
    assert len(items) == 1
    assert items[0].provenance == ("test",)
    assert items[0].confidence == 0.8
    assert items[0].action_capable is False


def test_recommendation_presentation_normalizes_whitespace() -> None:
    response = RecommendationResponse(recommendations=[
        Recommendation(
            kind="recommendation",
            text="  Review\n  the current   state. ",
            confidence=0.8,
            provenance=["test"],
            provider_id="sentinel-core",
            model_id="context-baseline-v1",
        )
    ])
    assert recommendation_presentations(response)[0].text == "Review the current state."


def test_recommendation_model_rejects_oversized_text() -> None:
    with pytest.raises(ValidationError, match="at most 2000 characters"):
        RecommendationResponse(recommendations=[
            Recommendation(
                kind="recommendation",
                text="x" * 2001,
                confidence=0.8,
                provenance=["test"],
                provider_id="sentinel-core",
                model_id="context-baseline-v1",
            )
        ])
