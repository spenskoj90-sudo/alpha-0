import os

from fastapi.testclient import TestClient

os.environ["SENTINEL_ADMIN_TOKEN"] = "admin-secret-test"
os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app.main import app, store
from app.main import rate_limiter

client = TestClient(app)


def test_admin_brute_force_lockout_blocks_even_valid_token():
    if hasattr(store, "failures"):
        store.failures.clear()
    for _ in range(5):
        denied = client.get("/v1/admin/games", headers={"X-Sentinel-Admin-Token": "wrong"})
        assert denied.status_code == 403
        assert denied.json()["code"] == "ADMIN_ACCESS_DENIED"
    locked = client.get("/v1/admin/games", headers={"X-Sentinel-Admin-Token": "admin-secret-test"})
    assert locked.status_code == 403
    assert locked.json()["code"] == "ADMIN_ACCESS_DENIED"


def test_admin_valid_token_succeeds_before_lockout():
    if hasattr(store, "failures"):
        store.failures.clear()
    ok = client.get("/v1/admin/games", headers={"X-Sentinel-Admin-Token": "admin-secret-test"})
    assert ok.status_code == 200
    assert "games" in ok.json()


def test_admin_rate_limit_returns_429_under_low_ceiling():
    original_limit = rate_limiter.limit
    original_hits = rate_limiter._hits
    try:
        rate_limiter.limit = 1
        rate_limiter._hits.clear()
        first = client.get("/v1/admin/games", headers={"X-Sentinel-Admin-Token": "admin-secret-test"})
        second = client.get("/v1/admin/games", headers={"X-Sentinel-Admin-Token": "admin-secret-test"})
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["code"] == "RATE_LIMITED"
    finally:
        rate_limiter.limit = original_limit
        rate_limiter._hits.clear()
