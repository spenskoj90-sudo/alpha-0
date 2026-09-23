from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.request_limits import RequestBodyLimitMiddleware, request_body_limit_from_env


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


def test_request_limit_env_parser_rejects_invalid_and_out_of_range_values():
    for value in ("not-an-int", "1", "999999999"):
        try:
            request_body_limit_from_env(value)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"expected invalid request limit for {value}")


def test_request_limit_env_parser_accepts_safety_bounds():
    assert request_body_limit_from_env("65536") == 65_536
    assert request_body_limit_from_env("8388608") == 8_388_608


def test_negative_content_length_is_rejected_with_bounded_error():
    client = build_client()
    response = client.post("/echo", content=b"", headers={"content-length": "-1"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CONTENT_LENGTH"
    assert response.json()["request_id"]


def test_request_id_is_preserved_on_rejection():
    response = build_client().post(
        "/echo",
        content=b"x" * 70_000,
        headers={"x-request-id": "limit-test-123"},
    )
    assert response.status_code == 413
    assert response.json()["request_id"] == "limit-test-123"
