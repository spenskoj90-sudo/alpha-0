from __future__ import annotations

from typing import Any, Mapping

from .ai_provider import AIProvider, AIProviderRegistry, AIProviderResult, BaselineRecommendationProvider


class RecommendationEngine:
    """Provider-neutral recommendation orchestration over normalized context."""

    def __init__(self, registry: AIProviderRegistry | None = None) -> None:
        self.registry = registry or AIProviderRegistry(
            providers=(BaselineRecommendationProvider(),),
            default_provider_id="sentinel-core",
        )

    def recommend(
        self,
        context: Mapping[str, Any],
        *,
        provider_id: str | None = None,
    ) -> AIProviderResult:
        provider: AIProvider = self.registry.route(provider_id)
        return provider.generate(context)
