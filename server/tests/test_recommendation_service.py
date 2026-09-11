from app.core.recommendation_delivery import DeliveredRecommendation
from app.core.recommendation_service import RecommendationService


class StubDelivery:
    def __init__(self) -> None:
        self.context = None
        self.provider_id = None

    def deliver(self, context, *, provider_id=None):
        self.context = context
        self.provider_id = provider_id
        return (
            DeliveredRecommendation(
                kind="recommendation",
                text="Review recent events.",
                confidence=0.72,
                provenance=("sentinel-core:test",),
                provider_id="sentinel-core",
                model_id="baseline-v1",
            ),
        )


def test_service_preserves_delivery_evidence_and_provider_selection():
    delivery = StubDelivery()
    response = RecommendationService(delivery).recommend(
        {"state": "bounded"},
        provider_id="sentinel-core",
    )

    assert delivery.context == {"state": "bounded"}
    assert delivery.provider_id == "sentinel-core"
    item = response.recommendations[0]
    assert item.provider_id == "sentinel-core"
    assert item.model_id == "baseline-v1"
    assert item.provenance == ["sentinel-core:test"]
