from app.core.recommendation_delivery import RecommendationDelivery


def test_delivery_preserves_provider_evidence() -> None:
    delivered = RecommendationDelivery().deliver({"state": "bounded"})

    assert len(delivered) == 1
    item = delivered[0]
    assert item.kind == "recommendation"
    assert item.text
    assert item.confidence == 0.72
    assert item.provenance == ("sentinel-core:context-baseline",)
    assert item.provider_id == "sentinel-core"
    assert item.model_id == "context-baseline-v1"


def test_delivery_routes_explicit_provider() -> None:
    delivered = RecommendationDelivery().deliver({}, provider_id="sentinel-core")

    assert delivered[0].provider_id == "sentinel-core"
    assert delivered[0].model_id == "context-baseline-v1"


def test_delivery_fails_closed_for_unknown_provider() -> None:
    try:
        RecommendationDelivery().deliver({}, provider_id="missing-provider")
    except KeyError as exc:
        assert str(exc).strip("'") == "AI_PROVIDER_NOT_REGISTERED"
    else:
        raise AssertionError("unknown providers must fail closed")
