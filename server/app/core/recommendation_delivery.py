from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .ai_provider import AIProviderResult
from .recommendation_engine import RecommendationEngine


@dataclass(frozen=True, slots=True)
class DeliveredRecommendation:
    """Provider-neutral recommendation plus its evidence identity."""

    kind: str
    text: str
    confidence: float
    provenance: tuple[str, ...]
    provider_id: str
    model_id: str


class RecommendationDelivery:
    """Convert engine output into a bounded presentation-ready contract.

    This layer remains observational: it does not authorize, execute, or
    persist actions and does not perform network I/O.
    """

    def __init__(self, engine: RecommendationEngine | None = None) -> None:
        self._engine = engine or RecommendationEngine()

    def deliver(
        self,
        context: Mapping[str, Any],
        *,
        provider_id: str | None = None,
    ) -> tuple[DeliveredRecommendation, ...]:
        result: AIProviderResult = self._engine.recommend(context, provider_id=provider_id)
        return (
            DeliveredRecommendation(
                kind=result.kind,
                text=result.text,
                confidence=result.confidence,
                provenance=result.provenance,
                provider_id=result.provider_id,
                model_id=result.model_id,
            ),
        )
