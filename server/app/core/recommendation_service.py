from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import RecommendationResponse
from .recommendation_api import recommendation_response
from .recommendation_delivery import RecommendationDelivery


class RecommendationService:
    """Bounded application seam between recommendation delivery and API models."""

    def __init__(self, delivery: RecommendationDelivery | None = None) -> None:
        self._delivery = delivery or RecommendationDelivery()

    def recommend(
        self,
        context: Mapping[str, Any],
        *,
        provider_id: str | None = None,
    ) -> RecommendationResponse:
        delivered = self._delivery.deliver(context, provider_id=provider_id)
        return recommendation_response(delivered)
