import os
import time

from fastapi.testclient import TestClient

ADMIN_TOKEN = "admin-secret-test"
TOTP_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
os.environ["SENTINEL_ADMIN_TOKEN"] = ADMIN_TOKEN
os.environ["SENTINEL_ADMIN_TOTP_SECRET"] = TOTP_SECRET
os.environ.setdefault("SENTINEL_ENROLLMENT_TOKEN", "u1:secret")
os.environ.setdefault("SENTINEL_REQUIRE_ENROLLMENT", "true")

from app.core.admin import _decode_totp_secret, _totp_at, verify_totp
from app.main import app, rate_limiter, store

client = TestClient(app)


def current_totp() -> str:
    return _totp_at(_decode_totp_secret(TOTP_SECRET), int(time.time() // 30))


def admin_headers(*, token: str = ADMIN_TOKEN, totp: str | None = None) -> dict[str, str]:
    return {
        "X-Sentinel-Admin-Token": token,
        "X-Sentinel-Admin-TOTP": totp or current_totp(),
    }


def reset_failures() -> None:
    if hasattr(store, "failures"):
        store.failures.clear()


def test_totp_matches_rfc6238_sha1_vector_at_59_seconds() -> None:
    assert verify_totp(TOTP_SECRET, "287082", now=59)


def test_admin_control_plane_fails_closed_without_totp_secret(monkeypatch) -> None:
    reset_failures()
    monkeypatch.delenv("SENTINEL_ADMIN_TOTP_SECRET", raising=False)
    response = client.get("/v1/admin/games", headers=admin_headers())
    assert response.status_code == 503
    assert response.json()["code"] == "ADMIN_CONTROL_PLANE_NOT_CONFIGURED"


def test_admin_valid_token_with_wrong_totp_is_denied() -> None:
    reset_failures()
    denied = client.get(
        "/v1/admin/games",
        headers=admin_headers(totp="000000" if current_totp() != "000000" else "999999"),
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "ADMIN_ACCESS_DENIED"


def test_admin_brute_force_lockout_blocks_even_valid_mfa():
    reset_failures()
    for _ in range(5):
        denied = client.get("/v1/admin/games", headers=admin_headers(token="wrong"))
        assert denied.status_code == 403
        assert denied.json()["code"] == "ADMIN_ACCESS_DENIED"
    locked = client.get("/v1/admin/games", headers=admin_headers())
    assert locked.status_code == 403
    assert locked.json()["code"] == "ADMIN_ACCESS_DENIED"


def test_admin_valid_mfa_succeeds_before_lockout():
    reset_failures()
    ok = client.get("/v1/admin/games", headers=admin_headers())
    assert ok.status_code == 200
    assert "games" in ok.json()


def test_admin_rate_limit_returns_429_under_low_ceiling():
    reset_failures()
    original_limit = rate_limiter.limit
    try:
        rate_limiter.limit = 1
        rate_limiter._hits.clear()
        first = client.get("/v1/admin/games", headers=admin_headers())
        second = client.get("/v1/admin/games", headers=admin_headers())
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["code"] == "RATE_LIMITED"
    finally:
        rate_limiter.limit = original_limit
        rate_limiter._hits.clear()
