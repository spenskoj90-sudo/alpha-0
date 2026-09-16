from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.request_limits import RequestBodyLimitMiddleware


def build_client(limit: int = 65_536) -> TestClient:
    inner = FastAPI()

    @inner.post("/echo")
    async def echo(request: Request):
        body = await request.body()
        return {"bytes": len(body)}

    return TestClient(RequestBodyLimitMiddleware(inner, max_body_bytes=limit))


def test_request_under_limit_reaches_application():
    response = build_client().post("/echo", content=b"x" * 1024)
    assert response.status_code == 200
    assert response.json() == {"bytes": 1024}


def test_advertised_oversize_request_is_rejected_before_application():
    response = build_client().post("/echo", content=b"x" * 70_000)
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_BODY_TOO_LARGE"
