from fastapi import HTTPException
from starlette.requests import Request

from app.core.models import RecommendationRequest, RecommendationResponse
from app.core.security import Principal
from app.core.wow_api import recommendations_v2


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/v1/recommendations", "headers": []})


def _authorized(monkeypatch) -> None:
    import app.main as main

    principal = Principal("user-1", None, frozenset(), frozenset({"game:read"}))
    monkeypatch.setattr(main, "require_bearer", lambda value: value)
    monkeypatch.setattr(main, "principal_from_token", lambda token: principal)
    monkeypatch.setattr(main, "authorize_request", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "request_id", lambda request, supplied=None: supplied or "request-generated")


def test_recommendation_endpoint_uses_application_provider_metadata(monkeypatch):
    _authorized(monkeypatch)
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


def test_recommendation_endpoint_fails_closed_for_unknown_provider(monkeypatch):
    _authorized(monkeypatch)

    try:
        recommendations_v2(
            RecommendationRequest(context={"state": "bounded"}),
            _request(),
            "Bearer test-token",
            "request-2",
            x_recommendation_provider="unknown-provider",
        )
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "'AI_PROVIDER_NOT_REGISTERED'"
    else:
        raise AssertionError("unknown provider was accepted")
