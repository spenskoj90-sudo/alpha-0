import pytest

from app.core.ai_provider import AIProviderRegistry, BaselineRecommendationProvider


def test_provider_description_is_sorted_and_bounded():
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry((provider,), default_provider_id=provider.provider_id)

    assert registry.provider_ids() == ("sentinel-core",)
    assert registry.describe() == ({"provider_id": "sentinel-core", "model_id": "context-baseline-v1", "default": True},)


def test_provider_description_does_not_expose_provider_internals():
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry((provider,))
    description = registry.describe()[0]

    assert set(description) == {"provider_id", "model_id", "default"}
    assert "generate" not in description


def test_duplicate_provider_registration_remains_fail_closed():
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry((provider,))
    with pytest.raises(ValueError, match="AI_PROVIDER_ALREADY_REGISTERED"):
        registry.register(provider)
