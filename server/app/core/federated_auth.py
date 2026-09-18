from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_MAX_JWT_BYTES = 16_384
_MAX_PROVIDER_RESPONSE_BYTES = 131_072
_GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
_TELEGRAM_JWKS = "https://oauth.telegram.org/.well-known/jwks.json"


class FederatedAuthError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedFederatedIdentity:
    provider: str
    subject: str
    email: str | None = None
    email_verified: bool = False


@dataclass(frozen=True)
class BrowserAuthStart:
    provider: str
    authorization_url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    enabled: bool
    flow: str
    client_id: str | None = None


def _enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes"}


def _safe_redirect_uri(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    if parsed.scheme == "https":
        return bool(parsed.hostname)
    return (
        parsed.scheme
        in {
            "com.alpha0.app.auth",
            "com.alpha0.app.auth.dev",
            "com.alpha0.app.physicaltest.auth",
        }
        and parsed.netloc == "callback"
        and parsed.path in {"", "/"}
    )


def _configured_redirect_uris(provider: str) -> tuple[str, ...]:
    env_name = f"SENTINEL_{provider.upper()}_REDIRECT_URIS"
    values = tuple(
        item.strip()
        for item in (os.getenv(env_name) or "").split(",")
        if item.strip()
    )
    return tuple(item for item in values if _safe_redirect_uri(item))


def provider_statuses() -> list[ProviderStatus]:
    google_id = (os.getenv("SENTINEL_GOOGLE_WEB_CLIENT_ID") or "").strip()
    telegram_id = (os.getenv("SENTINEL_TELEGRAM_CLIENT_ID") or "").strip()
    telegram_secret = (os.getenv("SENTINEL_TELEGRAM_CLIENT_SECRET") or "").strip()
    telegram_redirects = _configured_redirect_uris("telegram")
    vk_id = (os.getenv("SENTINEL_VK_CLIENT_ID") or "").strip()
    vk_redirects = _configured_redirect_uris("vk")
    return [
        ProviderStatus(
            provider="google",
            enabled=_enabled("SENTINEL_GOOGLE_AUTH_ENABLED") and bool(google_id),
            flow="credential-manager",
            client_id=google_id or None,
        ),
        ProviderStatus(
            provider="telegram",
            enabled=(
                _enabled("SENTINEL_TELEGRAM_AUTH_ENABLED")
                and bool(telegram_id)
                and bool(telegram_secret)
                and bool(telegram_redirects)
            ),
            flow="oidc-pkce",
            client_id=telegram_id or None,
        ),
        ProviderStatus(
            provider="vk",
            enabled=(
                _enabled("SENTINEL_VK_AUTH_ENABLED")
                and bool(vk_id)
                and bool(vk_redirects)
            ),
            flow="oauth-pkce",
            client_id=vk_id or None,
        ),
    ]


def provider_status(provider: str) -> ProviderStatus:
    normalized = provider.strip().lower()
    for status in provider_statuses():
        if status.provider == normalized:
            return status
    raise FederatedAuthError("AUTH_PROVIDER_UNSUPPORTED")


def _b64url_decode(value: str, *, max_bytes: int = _MAX_JWT_BYTES) -> bytes:
    if len(value) > max_bytes * 2:
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID")
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID") from exc
    if len(decoded) > max_bytes:
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID")
    return decoded


def _json_object(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID") from exc
    if not isinstance(value, dict):
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID")
    return value


def _https_json(
    url: str,
    *,
    allowed_hosts: set[str],
    method: str = "GET",
    form: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts or parsed.username or parsed.password:
        raise FederatedAuthError("FEDERATED_PROVIDER_ENDPOINT_INVALID")
    body = urlencode(form).encode("utf-8") if form is not None else None
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    if headers:
        request_headers.update(headers)
    req = Request(url, data=body, method=method, headers=request_headers)
    try:
        with urlopen(req, timeout=7) as response:
            raw = response.read(_MAX_PROVIDER_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise FederatedAuthError("FEDERATED_PROVIDER_UNAVAILABLE") from exc
    if len(raw) > _MAX_PROVIDER_RESPONSE_BYTES:
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_TOO_LARGE")
    return _json_object(raw)


def _verify_rs256_jwt(
    token: str,
    *,
    jwks_url: str,
    jwks_hosts: set[str],
    issuers: set[str],
    audience: str,
    nonce: str | None = None,
    now: int | None = None,
    jwks_fetcher: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not token or len(token.encode("utf-8")) > _MAX_JWT_BYTES:
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID")
    parts = token.split(".")
    if len(parts) != 3:
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID")
    header = _json_object(_b64url_decode(parts[0]))
    claims = _json_object(_b64url_decode(parts[1]))
    signature = _b64url_decode(parts[2])
    if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
        raise FederatedAuthError("FEDERATED_TOKEN_INVALID")
    jwks = jwks_fetcher() if jwks_fetcher else _https_json(jwks_url, allowed_hosts=jwks_hosts)
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID")
    selected = next(
        (
            key for key in keys
            if isinstance(key, dict)
            and key.get("kid") == header["kid"]
            and key.get("kty") == "RSA"
        ),
        None,
    )
    if not isinstance(selected, dict) or not isinstance(selected.get("n"), str) or not isinstance(selected.get("e"), str):
        raise FederatedAuthError("FEDERATED_SIGNING_KEY_UNKNOWN")
    try:
        n = int.from_bytes(_b64url_decode(selected["n"]), "big")
        e = int.from_bytes(_b64url_decode(selected["e"]), "big")
        public_key = rsa.RSAPublicNumbers(e, n).public_key()
        public_key.verify(
            signature,
            f"{parts[0]}.{parts[1]}".encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as exc:
        raise FederatedAuthError("FEDERATED_TOKEN_SIGNATURE_INVALID") from exc

    current = int(time.time()) if now is None else now
    issuer = claims.get("iss")
    subject = claims.get("sub")
    exp = claims.get("exp")
    iat = claims.get("iat")
    audiences = claims.get("aud")
    audience_values = audiences if isinstance(audiences, list) else [audiences]
    if issuer not in issuers or not isinstance(subject, str) or not subject or len(subject) > 512:
        raise FederatedAuthError("FEDERATED_TOKEN_CLAIMS_INVALID")
    if audience not in audience_values:
        raise FederatedAuthError("FEDERATED_TOKEN_AUDIENCE_INVALID")
    if len(audience_values) > 1 and claims.get("azp") != audience:
        raise FederatedAuthError("FEDERATED_TOKEN_AUDIENCE_INVALID")
    if not isinstance(exp, int) or exp <= current - 30:
        raise FederatedAuthError("FEDERATED_TOKEN_EXPIRED")
    if not isinstance(iat, int) or iat > current + 120:
        raise FederatedAuthError("FEDERATED_TOKEN_CLAIMS_INVALID")
    if nonce is not None:
        received_nonce = claims.get("nonce")
        if not isinstance(received_nonce, str) or not hmac.compare_digest(received_nonce, nonce):
            raise FederatedAuthError("FEDERATED_NONCE_INVALID")
    return claims


def verify_google_id_token(
    id_token: str,
    nonce: str,
    *,
    now: int | None = None,
    jwks_fetcher: Callable[[], dict[str, Any]] | None = None,
) -> VerifiedFederatedIdentity:
    status = provider_status("google")
    if not status.enabled or not status.client_id:
        raise FederatedAuthError("AUTH_PROVIDER_NOT_CONFIGURED")
    claims = _verify_rs256_jwt(
        id_token,
        jwks_url=_GOOGLE_JWKS,
        jwks_hosts={"www.googleapis.com"},
        issuers={"accounts.google.com", "https://accounts.google.com"},
        audience=status.client_id,
        nonce=nonce,
        now=now,
        jwks_fetcher=jwks_fetcher,
    )
    email = claims.get("email")
    if not isinstance(email, str) or "@" not in email:
        email = None
    verified_value = claims.get("email_verified")
    provider_verified = verified_value is True or verified_value == "true"
    authoritative_email = bool(
        email
        and provider_verified
        and (email.lower().endswith("@gmail.com") or isinstance(claims.get("hd"), str))
    )
    return VerifiedFederatedIdentity(
        provider="google",
        subject=str(claims["sub"]),
        email=email.lower() if email else None,
        email_verified=authoritative_email,
    )


def start_browser_flow(provider: str, state: str, redirect_uri: str) -> BrowserAuthStart:
    normalized = provider.strip().lower()
    status = provider_status(normalized)
    if not status.enabled or not status.client_id:
        raise FederatedAuthError("AUTH_PROVIDER_NOT_CONFIGURED")
    if normalized not in {"telegram", "vk"}:
        raise FederatedAuthError("AUTH_PROVIDER_FLOW_INVALID")
    if redirect_uri not in _configured_redirect_uris(normalized):
        raise FederatedAuthError("FEDERATED_REDIRECT_URI_INVALID")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    if normalized == "telegram":
        params = {
            "client_id": status.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "nonce": state,
        }
        endpoint = "https://oauth.telegram.org/auth"
    else:
        params = {
            "client_id": status.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        endpoint = "https://id.vk.ru/authorize"
    return BrowserAuthStart(normalized, f"{endpoint}?{urlencode(params)}", state, verifier)


def complete_telegram(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    nonce: str | None = None,
    now: int | None = None,
    token_fetcher: Callable[[], dict[str, Any]] | None = None,
    jwks_fetcher: Callable[[], dict[str, Any]] | None = None,
) -> VerifiedFederatedIdentity:
    status = provider_status("telegram")
    client_secret = (os.getenv("SENTINEL_TELEGRAM_CLIENT_SECRET") or "").strip()
    if not status.enabled or not status.client_id or not client_secret:
        raise FederatedAuthError("AUTH_PROVIDER_NOT_CONFIGURED")
    if redirect_uri not in _configured_redirect_uris("telegram"):
        raise FederatedAuthError("FEDERATED_REDIRECT_URI_INVALID")
    if token_fetcher:
        token_result = token_fetcher()
    else:
        basic = base64.b64encode(f"{status.client_id}:{client_secret}".encode()).decode()
        token_result = _https_json(
            "https://oauth.telegram.org/token",
            allowed_hosts={"oauth.telegram.org"},
            method="POST",
            headers={"Authorization": f"Basic {basic}"},
            form={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": status.client_id,
                "code_verifier": code_verifier,
            },
        )
    id_token = token_result.get("id_token")
    if not isinstance(id_token, str):
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID")
    claims = _verify_rs256_jwt(
        id_token,
        jwks_url=_TELEGRAM_JWKS,
        jwks_hosts={"oauth.telegram.org"},
        issuers={"https://oauth.telegram.org"},
        audience=status.client_id,
        nonce=nonce,
        now=now,
        jwks_fetcher=jwks_fetcher,
    )
    return VerifiedFederatedIdentity(provider="telegram", subject=str(claims["sub"]))


def complete_vk(
    *,
    code: str,
    state: str,
    code_verifier: str,
    device_id: str,
    redirect_uri: str,
    token_fetcher: Callable[[], dict[str, Any]] | None = None,
    user_fetcher: Callable[[str], dict[str, Any]] | None = None,
) -> VerifiedFederatedIdentity:
    status = provider_status("vk")
    if not status.enabled or not status.client_id:
        raise FederatedAuthError("AUTH_PROVIDER_NOT_CONFIGURED")
    if redirect_uri not in _configured_redirect_uris("vk"):
        raise FederatedAuthError("FEDERATED_REDIRECT_URI_INVALID")
    if token_fetcher:
        token_result = token_fetcher()
    else:
        token_result = _https_json(
            "https://id.vk.ru/oauth2/auth",
            allowed_hosts={"id.vk.ru"},
            method="POST",
            form={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": status.client_id,
                "device_id": device_id,
                "redirect_uri": redirect_uri,
                "state": state,
            },
        )
    returned_state = token_result.get("state")
    if isinstance(returned_state, str) and not hmac.compare_digest(returned_state, state):
        raise FederatedAuthError("FEDERATED_STATE_INVALID")
    access_token = token_result.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID")
    if user_fetcher:
        user_result = user_fetcher(access_token)
    else:
        user_result = _https_json(
            f"https://id.vk.ru/oauth2/user_info?{urlencode({'client_id': status.client_id})}",
            allowed_hosts={"id.vk.ru"},
            method="POST",
            form={
                "access_token": access_token,
                "device_id": device_id,
            },
        )
    candidate = user_result.get("user")
    user = candidate if isinstance(candidate, dict) else user_result
    subject = user.get("user_id", user.get("id"))
    if not isinstance(subject, (str, int)) or not str(subject):
        raise FederatedAuthError("FEDERATED_PROVIDER_RESPONSE_INVALID")
    email = user.get("email")
    return VerifiedFederatedIdentity(
        provider="vk",
        subject=str(subject),
        email=email.lower() if isinstance(email, str) and "@" in email else None,
        email_verified=False,
    )
