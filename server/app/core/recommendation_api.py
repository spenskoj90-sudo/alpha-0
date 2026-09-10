from __future__ import annotations

from collections.abc import Iterable

from .models import Recommendation, RecommendationResponse
from .recommendation_delivery import DeliveredRecommendation


def recommendation_response(
    recommendations: Iterable[DeliveredRecommendation],
) -> RecommendationResponse:
    """Map bounded delivery results to the public API response contract."""

    return RecommendationResponse(
        recommendations=[
            Recommendation(
                kind=item.kind,
                text=item.text,
                confidence=item.confidence,
                provenance=list(item.provenance),
                provider_id=item.provider_id,
                model_id=item.model_id,
            )
            for item in recommendations
        ]
    )
