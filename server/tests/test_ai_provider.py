from __future__ import annotations

import pytest

from app.core.ai_provider import AIProviderRegistry, AIProviderResult, BaselineRecommendationProvider


def test_baseline_provider_is_deterministic_and_carries_provenance() -> None:
    provider = BaselineRecommendationProvider()

    first = provider.generate({"state_id": "a", "sequence": 1})
    second = provider.generate({"state_id": "b", "sequence": 2})

    assert first == second
    assert first.kind == "recommendation"
    assert first.confidence == 0.72
    assert first.provenance == ("sentinel-core:context-baseline",)
    assert first.provider_id == "sentinel-core"
    assert first.model_id == "context-baseline-v1"


def test_registry_routes_explicit_and_default_provider() -> None:
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry((provider,), default_provider_id=provider.provider_id)

    assert registry.route() is provider
    assert registry.route("sentinel-core") is provider
    assert registry.provider_ids() == ("sentinel-core",)


def test_registry_fails_closed_for_unknown_provider() -> None:
    registry = AIProviderRegistry((BaselineRecommendationProvider(),))

    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED"):
        registry.route()
    with pytest.raises(KeyError, match="AI_PROVIDER_NOT_REGISTERED"):
        registry.route("missing")


def test_registry_rejects_duplicate_provider_ids() -> None:
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry((provider,))

    with pytest.raises(ValueError, match="AI_PROVIDER_ALREADY_REGISTERED"):
        registry.register(provider)


def test_result_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="AI_RESULT_CONFIDENCE_INVALID"):
        AIProviderResult(
            kind="recommendation",
            text="x",
            confidence=1.1,
            provenance=("test",),
            provider_id="test",
            model_id="test",
        )
