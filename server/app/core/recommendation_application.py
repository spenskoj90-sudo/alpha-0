from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import RecommendationResponse
from .recommendation_service import RecommendationService


class RecommendationApplication:
    """Application-facing recommendation seam; authorization stays at the API boundary."""

    def __init__(self, service: RecommendationService | None = None) -> None:
        self._service = service or RecommendationService()

    def recommend(
        self,
        context: Mapping[str, Any],
        *,
        provider_id: str | None = None,
    ) -> RecommendationResponse:
        return self._service.recommend(context, provider_id=provider_id)
