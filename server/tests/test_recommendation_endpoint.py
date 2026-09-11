from fastapi import HTTPException
from starlette.requests import Request

from app.core.models import RecommendationRequest, RecommendationResponse
from app.core.wow_api import recommendations_v2


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/v1/recommendations", "headers": []})


def test_recommendation_endpoint_uses_application_provider_metadata():
    response = recommendations_v2(
        RecommendationRequest(context={"state": "bounded"}),
        _request(),
        "Bearer test-token",
        "request-1",
    )

    assert isinstance(response, RecommendationResponse)
    assert len(response.recommendations) == 1
    item = response.recommendations[0]
    assert item.provider_id == "sentinel-core"
    assert item.model_id == "context-baseline-v1"
    assert item.provenance == ["sentinel-core:context-baseline"]


def test_recommendation_endpoint_fails_closed_for_unknown_provider():
    try:
        recommendations_v2(
            RecommendationRequest(context={"state": "bounded"}),
            _request(),
            "Bearer test-token",
            "request-2",
            "unknown-provider",
        )
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "'AI_PROVIDER_NOT_REGISTERED'"
    else:
        raise AssertionError("unknown provider was accepted")
