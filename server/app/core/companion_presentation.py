from __future__ import annotations

from uuid import uuid4

from .companion_health_api import companion_health_response
from .companion_interaction import (
    CompanionPresentation,
    CompanionPresentationChannel,
    CompanionPresentationKind,
)
from .companion_presentation_policy import bound_presentation_text, validate_recommendation_metadata
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
    text = bound_presentation_text(
        f"Companion status: {mode}. Queue {snapshot['queue_depth']}, latency "
        f"{snapshot['last_latency_ms'] if snapshot['last_latency_ms'] is not None else 'n/a'} ms."
    )
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
    presentations: list[CompanionPresentation] = []
    for item in response.recommendations:
        metadata = validate_recommendation_metadata(
            provider_id=item.provider_id,
            model_id=item.model_id,
            provenance=tuple(item.provenance),
            confidence=item.confidence,
        )
        presentations.append(
            CompanionPresentation(
                channel=channel,
                kind=CompanionPresentationKind.RECOMMENDATION,
                text=bound_presentation_text(item.text),
                correlation_id=uuid4(),
                provenance=metadata.provenance,
                confidence=metadata.confidence,
            )
        )
    return tuple(presentations)
