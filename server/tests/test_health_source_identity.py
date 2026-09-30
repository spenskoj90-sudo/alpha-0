from fastapi.testclient import TestClient
from app.main import app


def test_health_correlates_with_exact_render_build(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json()["source_sha"] == "a" * 40


def test_health_does_not_echo_invalid_build_identity(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "arbitrary-private-value")
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    response = TestClient(app).get("/healthz")
    assert response.json().get("source_sha") is None
    assert "arbitrary-private-value" not in response.text
