from __future__ import annotations

import base64
import json
import time
from types import SimpleNamespace
from urllib.error import URLError

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

import app.core.federated_auth as federated
from app.core.federated_auth import FederatedAuthError


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture(scope="module")
def rsa_material():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "boundary-key",
        "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }
    return private, {"keys": [jwk]}


def _token(private, claims: dict, *, header: dict | None = None) -> str:
    header = header or {"alg": "RS256", "kid": "boundary-key"}
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode())
    encoded_claims = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signed = f"{encoded_header}.{encoded_claims}".encode("ascii")
    signature = private.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_claims}.{_b64url(signature)}"


def _claims(now: int) -> dict:
    return {
        "iss": "https://issuer.example",
        "sub": "subject-123",
        "aud": "sentinel-client",
        "iat": now,
        "exp": now + 300,
        "nonce": "nonce-123",
    }


def _verify(token: str, jwks: dict, *, now: int, nonce: str | None = "nonce-123"):
    return federated._verify_rs256_jwt(
        token,
        jwks_url="https://issuer.example/jwks",
        jwks_hosts={"issuer.example"},
        issuers={"https://issuer.example"},
        audience="sentinel-client",
        nonce=nonce,
        now=now,
        jwks_fetcher=lambda: jwks,
    )


@pytest.mark.parametrize(
    ("value", "safe"),
    [
        ("https://example.test/callback", True),
        ("https://user@example.test/callback", False),
        ("https://example.test/callback?code=x", False),
        ("https://example.test/callback#fragment", False),
        ("com.alpha0.app.auth://callback", True),
        ("com.alpha0.app.auth.dev://callback/", True),
        ("com.alpha0.app.physicaltest.auth://callback", True),
        ("com.alpha0.app.auth://other", False),
        ("vk123456://vk.ru/blank.html", True),
        ("vkabc://vk.ru/blank.html", False),
        ("javascript://callback", False),
    ],
)
def test_redirect_allowlist_accepts_only_explicit_safe_shapes(value: str, safe: bool) -> None:
    assert federated._safe_redirect_uri(value) is safe


def test_provider_status_rejects_unknown_provider(monkeypatch) -> None:
    for name in (
        "SENTINEL_GOOGLE_AUTH_ENABLED",
        "SENTINEL_TELEGRAM_AUTH_ENABLED",
        "SENTINEL_VK_AUTH_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(FederatedAuthError, match="AUTH_PROVIDER_UNSUPPORTED"):
        federated.provider_status("unknown")


@pytest.mark.parametrize("value", ["***", "a" * 40000])
def test_b64_decoder_bounds_malformed_tokens(value: str) -> None:
    with pytest.raises(FederatedAuthError, match="FEDERATED_TOKEN_INVALID"):
        federated._b64url_decode(value, max_bytes=16)


@pytest.mark.parametrize("raw", [b"{", b"[]", b"null"])
def test_json_object_rejects_non_object_provider_payloads(raw: bytes) -> None:
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_INVALID"):
        federated._json_object(raw)


def test_https_json_rejects_endpoint_confusion_and_bounds_provider_io(monkeypatch) -> None:
    for url in (
        "http://issuer.example/api",
        "https://user@issuer.example/api",
        "https://evil.example/api",
    ):
        with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_ENDPOINT_INVALID"):
            federated._https_json(url, allowed_hosts={"issuer.example"})

    monkeypatch.setattr(
        federated,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("private network detail")),
    )
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_UNAVAILABLE"):
        federated._https_json("https://issuer.example/api", allowed_hosts={"issuer.example"})

    class Response:
        def __init__(self, raw: bytes) -> None:
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return self.raw

    monkeypatch.setattr(
        federated,
        "urlopen",
        lambda *_args, **_kwargs: Response(b"x" * (131_072 + 1)),
    )
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_TOO_LARGE"):
        federated._https_json("https://issuer.example/api", allowed_hosts={"issuer.example"})

    captured = {}

    def open_ok(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response(b'{"ok":true}')

    monkeypatch.setattr(federated, "urlopen", open_ok)
    assert federated._https_json(
        "https://issuer.example/token",
        allowed_hosts={"issuer.example"},
        method="POST",
        form={"code": "safe"},
        headers={"Authorization": "Basic opaque"},
    ) == {"ok": True}
    assert captured["timeout"] == 7
    assert captured["request"].data == b"code=safe"
    assert captured["request"].headers["Authorization"] == "Basic opaque"


def test_jwt_verifier_rejects_structural_and_key_failures(rsa_material) -> None:
    private, jwks = rsa_material
    now = int(time.time())

    for token in ("", "one.two", "a" * 20000):
        with pytest.raises(FederatedAuthError, match="FEDERATED_TOKEN_INVALID"):
            _verify(token, jwks, now=now)

    bad_alg = _token(private, _claims(now), header={"alg": "HS256", "kid": "boundary-key"})
    with pytest.raises(FederatedAuthError, match="FEDERATED_TOKEN_INVALID"):
        _verify(bad_alg, jwks, now=now)

    valid = _token(private, _claims(now))
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_INVALID"):
        _verify(valid, {"keys": {}}, now=now)
    with pytest.raises(FederatedAuthError, match="FEDERATED_SIGNING_KEY_UNKNOWN"):
        _verify(valid, {"keys": [{"kty": "RSA", "kid": "other", "n": "x", "e": "x"}]}, now=now)

    parts = valid.split(".")
    tampered = f"{parts[0]}.{_b64url(json.dumps({**_claims(now), 'sub': 'attacker'}).encode())}.{parts[2]}"
    with pytest.raises(FederatedAuthError, match="FEDERATED_TOKEN_SIGNATURE_INVALID"):
        _verify(tampered, jwks, now=now)


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda c: {**c, "iss": "https://wrong.example"}, "FEDERATED_TOKEN_CLAIMS_INVALID"),
        (lambda c: {**c, "sub": ""}, "FEDERATED_TOKEN_CLAIMS_INVALID"),
        (lambda c: {**c, "aud": "other-client"}, "FEDERATED_TOKEN_AUDIENCE_INVALID"),
        (lambda c: {**c, "aud": ["sentinel-client", "other"], "azp": "other"}, "FEDERATED_TOKEN_AUDIENCE_INVALID"),
        (lambda c: {**c, "exp": 1}, "FEDERATED_TOKEN_EXPIRED"),
        (lambda c: {**c, "iat": c["iat"] + 121}, "FEDERATED_TOKEN_CLAIMS_INVALID"),
        (lambda c: {**c, "nonce": "wrong"}, "FEDERATED_NONCE_INVALID"),
    ],
)
def test_jwt_verifier_fails_closed_on_security_claim_mismatch(rsa_material, mutate, error: str) -> None:
    private, jwks = rsa_material
    now = int(time.time())
    token = _token(private, mutate(_claims(now)))
    with pytest.raises(FederatedAuthError, match=error):
        _verify(token, jwks, now=now)


def test_multi_audience_token_requires_authorized_party(rsa_material) -> None:
    private, jwks = rsa_material
    now = int(time.time())
    claims = {**_claims(now), "aud": ["sentinel-client", "other"], "azp": "sentinel-client"}
    assert _verify(_token(private, claims), jwks, now=now)["sub"] == "subject-123"


def test_browser_flow_and_provider_completion_reject_mismatched_configuration(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_GOOGLE_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_GOOGLE_WEB_CLIENT_ID", "client")
    with pytest.raises(FederatedAuthError, match="AUTH_PROVIDER_FLOW_INVALID"):
        federated.start_browser_flow("google", "state", "https://example.test/callback")

    monkeypatch.setenv("SENTINEL_TELEGRAM_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_ID", "123")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SENTINEL_TELEGRAM_REDIRECT_URIS", "com.alpha0.app.auth://callback")
    with pytest.raises(FederatedAuthError, match="FEDERATED_REDIRECT_URI_INVALID"):
        federated.complete_telegram(
            code="code",
            code_verifier="v" * 64,
            redirect_uri="com.alpha0.app.auth.dev://callback",
            token_fetcher=lambda: {},
        )
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_INVALID"):
        federated.complete_telegram(
            code="code",
            code_verifier="v" * 64,
            redirect_uri="com.alpha0.app.auth://callback",
            token_fetcher=lambda: {},
        )


def test_vk_completion_validates_state_token_subject_and_email(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_VK_AUTH_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_VK_CLIENT_ID", "123456")
    monkeypatch.setenv("SENTINEL_VK_REDIRECT_URIS", "vk123456://vk.ru/blank.html")
    kwargs = {
        "code": "code",
        "state": "expected",
        "code_verifier": "v" * 64,
        "device_id": "device",
        "redirect_uri": "vk123456://vk.ru/blank.html",
    }

    with pytest.raises(FederatedAuthError, match="FEDERATED_STATE_INVALID"):
        federated.complete_vk(
            **kwargs,
            token_fetcher=lambda: {"access_token": "token", "state": "wrong"},
            user_fetcher=lambda _token: {"user_id": 1},
        )
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_INVALID"):
        federated.complete_vk(
            **kwargs,
            token_fetcher=lambda: {"state": "expected"},
            user_fetcher=lambda _token: {"user_id": 1},
        )
    with pytest.raises(FederatedAuthError, match="FEDERATED_PROVIDER_RESPONSE_INVALID"):
        federated.complete_vk(
            **kwargs,
            token_fetcher=lambda: {"access_token": "token", "state": "expected"},
            user_fetcher=lambda _token: {"user": {}},
        )

    identity = federated.complete_vk(
        **kwargs,
        token_fetcher=lambda: {"access_token": "token", "state": "expected"},
        user_fetcher=lambda _token: {"id": "subject", "email": "not-an-email"},
    )
    assert identity.subject == "subject"
    assert identity.email is None
    assert identity.email_verified is False
