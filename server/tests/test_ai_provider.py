from app.core.ai_provider import AIProviderRegistry, BaselineRecommendationProvider


def test_provider_registry_routes_default_and_explicit_provider() -> None:
    provider = BaselineRecommendationProvider()
    registry = AIProviderRegistry(providers=(provider,), default_provider_id="sentinel-core")

    assert registry.route() is provider
    assert registry.route("sentinel-core") is provider
    assert registry.provider_ids() == ("sentinel-core",)
    assert registry.describe() == (
        {"provider_id": "sentinel-core", "model_id": "context-baseline-v2", "default": True},
    )


def test_provider_registry_fails_closed_for_unknown_provider() -> None:
    registry = AIProviderRegistry(providers=(BaselineRecommendationProvider(),), default_provider_id="sentinel-core")

    try:
        registry.route("external-provider-not-registered")
    except KeyError as exc:
        assert str(exc) == "'AI_PROVIDER_NOT_REGISTERED'"
    else:
        raise AssertionError("unknown providers must fail closed")


def test_baseline_provider_uses_knowledge_evidence() -> None:
    provider = BaselineRecommendationProvider()
    result = provider.generate(
        {
            "data_quality": "high",
            "player": {"level": 27, "alive": True},
            "events": [{"event_type": "mission_completed", "sequence": 1}],
        }
    )

    assert result.confidence == 0.76
    assert "character:level:27" in result.provenance
    assert "event:mission_completed" in result.provenance
    assert "recommendation:progression-review" in result.provenance
