from app.core.recommendation_application import RecommendationApplication
from app.core.recommendation_delivery import DeliveredRecommendation


class StubService:
    def recommend(self, context, *, provider_id=None):
        return type("Response", (), {"recommendations": [
            type("Recommendation", (), {
                "kind": "recommendation",
                "text": "Review recent events.",
                "confidence": 0.72,
                "provenance": ["sentinel-core:test"],
                "provider_id": "sentinel-core",
                "model_id": "baseline-v1",
            })()
        ]})()


def test_application_forwards_context_and_provider():
    service = StubService()
    response = RecommendationApplication(service).recommend({"state": "bounded"}, provider_id="sentinel-core")
    item = response.recommendations[0]
    assert item.provider_id == "sentinel-core"
    assert item.model_id == "baseline-v1"
    assert item.provenance == ["sentinel-core:test"]
