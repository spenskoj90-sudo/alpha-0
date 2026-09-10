from app.core.recommendation_api import recommendation_response
from app.core.recommendation_delivery import DeliveredRecommendation


def test_recommendation_response_preserves_delivery_evidence() -> None:
    result = recommendation_response(
        [
            DeliveredRecommendation(
                kind="recommendation",
                text="Review recent character events.",
                confidence=0.72,
                provenance=("sentinel-core:context-baseline",),
                provider_id="sentinel-core",
                model_id="baseline-v1",
            )
        ]
    )

    assert len(result.recommendations) == 1
    item = result.recommendations[0]
    assert item.kind == "recommendation"
    assert item.text == "Review recent character events."
    assert item.confidence == 0.72
    assert item.provenance == ["sentinel-core:context-baseline"]
    assert item.provider_id == "sentinel-core"
    assert item.model_id == "baseline-v1"


def test_recommendation_response_accepts_empty_delivery() -> None:
    assert recommendation_response([]).recommendations == []
