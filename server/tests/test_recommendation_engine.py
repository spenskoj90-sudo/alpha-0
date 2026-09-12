from typing import Any, Mapping

import pytest

from app.core.ai_provider import AIProviderRegistry, AIProviderResult
from app.core.recommendation_engine import RecommendationEngine


class StubProvider:
    provider_id = "stub"
    model_id = "stub-v1"

    def generate(self, context: Mapping[str, Any]) -> AIProviderResult:
        return AIProviderResult(
            kind="inference",
            text=f"signals={len(context)}",
            confidence=0.5,
            provenance=("stub:test",),
            provider_id=self.provider_id,
            model_id=self.model_id,
        )


def test_default_engine_routes_to_deterministic_baseline_provider() -> None:
    engine = RecommendationEngine()
    first = engine.recommend({"sequence": 1})
    second = engine.recommend({"sequence": 2})

    assert first == second
    assert first.kind == "recommendation"
    assert first.confidence == 0.40
    assert first.provenance == (
        "knowledge:insufficient-context",
        "recommendation:suppressed-low-evidence",
    )
    assert first.provider_id == "sentinel-core"
    assert first.model_id == "context-baseline-v1"


def test_engine_routes_explicit_provider_and_preserves_context() -> None:
    provider = StubProvider()
    engine = RecommendationEngine(
        AIProviderRegistry(providers=(provider,), default_provider_id="stub")
    )

    result = engine.recommend({"a": 1, "b": 2})

    assert result.kind == "inference"
    assert result.text == "signals=2"
    assert result.provider_id == "stub"
    assert result.model_id == "stub-v1"


def test_engine_fails_closed_for_unknown_provider() -> None:
    engine = RecommendationEngine()

    with pytest.raises(KeyError, match="AI_PROVIDER_NOT_REGISTERED"):
        engine.recommend({}, provider_id="missing")
