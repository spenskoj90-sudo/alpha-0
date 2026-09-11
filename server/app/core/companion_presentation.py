from __future__ import annotations

from uuid import uuid4

from .companion_health_api import companion_health_response
from .companion_interaction import (
    CompanionPresentation,
    CompanionPresentationChannel,
    CompanionPresentationKind,
)
from .companion_transport import CompanionRuntimeHealth
from .models import RecommendationResponse


def health_presentation(
    health: CompanionRuntimeHealth,
    *,
    channel: CompanionPresentationChannel = CompanionPresentationChannel.OVERLAY,
) -> CompanionPresentation:
    """Convert bounded health state into presentation-only status text."""
    snapshot = companion_health_response(health)
    mode = snapshot["mode"]
    text = f"Companion status: {mode}. Queue {snapshot['queue_depth']}, latency {snapshot['last_latency_ms'] if snapshot['last_latency_ms'] is not None else 'n/a'} ms."
    return CompanionPresentation(
        channel=channel,
        kind=CompanionPresentationKind.STATUS,
        text=text,
        correlation_id=uuid4(),
    )


def recommendation_presentations(
    response: RecommendationResponse,
    *,
    channel: CompanionPresentationChannel = CompanionPresentationChannel.OVERLAY,
) -> tuple[CompanionPresentation, ...]:
    """Map API recommendations into bounded presentation messages."""
    return tuple(
        CompanionPresentation(
            channel=channel,
            kind=CompanionPresentationKind.RECOMMENDATION,
            text=item.text,
            correlation_id=uuid4(),
            provenance=tuple(item.provenance),
            confidence=item.confidence,
        )
        for item in response.recommendations
    )
