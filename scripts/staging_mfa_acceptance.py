#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


BASE_URL = os.environ.get(
    "SENTINEL_STAGING_BASE_URL",
    "https://sentinel-core-staging.onrender.com",
).rstrip("/")
TIMEOUT_SECONDS = 45


class ApiFailure(RuntimeError):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"HTTP {status}: {code}")
        self.status = status
        self.code = code


def _safe_error_code(raw: bytes, fallback: str) -> str:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return fallback
    value = payload.get("code") or payload.get("detail")
    return str(value) if value else fallback


def request_json(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    bearer: str | None = None,
) -> dict:
    body = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "sentinel-staging-mfa-acceptance/1",
    }
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise ApiFailure(exc.code, _safe_error_code(raw, exc.reason or "HTTP_ERROR")) from None


def expect_failure(
    method: str,
    path: str,
    *,
    status: int,
    payload: dict | None = None,
    bearer: str | None = None,
) -> str:
    try:
        request_json(method, path, payload=payload, bearer=bearer)
    except ApiFailure as exc:
        if exc.status != status:
            raise AssertionError(
                f"{method} {path}: expected HTTP {status}, got {exc.status} ({exc.code})"
            ) from exc
        return exc.code
    raise AssertionError(f"{method} {path}: expected HTTP {status}, request succeeded")


def totp(secret: str, counter: int) -> str:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def current_counter() -> int:
    return int(time.time() // 30)


def wait_for_counter_after(counter: int) -> int:
    while True:
        now = current_counter()
        if now > counter:
            return now
        time.sleep(1)


def new_device_payload() -> dict:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {
        "platform": "android",
        "public_key_der_b64": base64.b64encode(public_der).decode("ascii"),
        "fingerprint_sha256": hashlib.sha256(public_der).hexdigest(),
    }


def require_session(payload: dict, context: str) -> str:
    token = payload.get("session_token")
    if not isinstance(token, str) or not token:
        raise AssertionError(f"{context}: session_token missing")
    return token


def require_mfa_challenge(payload: dict, context: str) -> str:
    if payload.get("mfa_required") is not True:
        raise AssertionError(f"{context}: mfa_required != true")
    if "session_token" in payload:
        raise AssertionError(f"{context}: first factor unexpectedly issued a session")
    token = payload.get("challenge_token")
    if not isinstance(token, str) or not token:
        raise AssertionError(f"{context}: challenge_token missing")
    return token


def main() -> int:
    print("step=health")
    health = request_json("GET", "/healthz")
    if health.get("status") != "UP":
        raise AssertionError("healthz did not report UP")

    suffix = uuid.uuid4().hex
    email = f"mfa-acceptance-{suffix}@example.invalid"
    password = "Mfa-Acceptance-" + secrets.token_urlsafe(24) + "-A1!"

    print("step=register")
    registered = request_json(
        "POST",
        "/v1/auth/register",
        payload={"email": email, "password": password},
    )
    initial_session = require_session(registered, "register")

    print("step=bind_initial_device")
    request_json(
        "POST",
        "/v1/devices/bind",
        payload=new_device_payload(),
        bearer=initial_session,
    )

    print("step=pre_mfa_state")
    pre = request_json("GET", "/v1/account/security", bearer=initial_session)
    if pre.get("mfa_enabled") is not False:
        raise AssertionError("new disposable account unexpectedly has MFA enabled")

    print("step=enroll_totp")
    try:
        enrollment = request_json(
            "POST",
            "/v1/account/mfa/totp/enroll",
            bearer=initial_session,
        )
    except ApiFailure as exc:
        if exc.status == 503 and exc.code in {
            "ACCOUNT_MFA_KEY_NOT_CONFIGURED",
            "ACCOUNT_MFA_KEY_INVALID",
            "ACCOUNT_MFA_SECRET_UNREADABLE",
        }:
            print(f"STAGING_MFA_ACCEPTANCE=BLOCKED code={exc.code}")
            return 3
        raise

    secret = enrollment.get("secret")
    if not isinstance(secret, str) or len(secret) < 16:
        raise AssertionError("enrollment secret missing")

    confirm_counter = current_counter()
    print("step=confirm_totp")
    confirmed = request_json(
        "POST",
        "/v1/account/mfa/totp/confirm",
        payload={"code": totp(secret, confirm_counter)},
        bearer=initial_session,
    )
    if confirmed.get("status") != "MFA_ENABLED":
        raise AssertionError("MFA confirmation did not return MFA_ENABLED")
    recovery_codes = confirmed.get("recovery_codes")
    if not isinstance(recovery_codes, list) or len(recovery_codes) != 10:
        raise AssertionError("expected 10 recovery codes")

    print("step=confirm_revokes_existing_session")
    expect_failure(
        "GET",
        "/v1/account/security",
        status=401,
        bearer=initial_session,
    )

    print("step=password_first_factor_requires_mfa")
    first = request_json(
        "POST",
        "/v1/auth/login",
        payload={"email": email, "password": password},
    )
    challenge = require_mfa_challenge(first, "password login")

    login_counter = wait_for_counter_after(confirm_counter)
    print("step=complete_with_totp")
    completed_totp = request_json(
        "POST",
        "/v1/auth/mfa/complete",
        payload={"challenge_token": challenge, "code": totp(secret, login_counter)},
    )
    totp_session = require_session(completed_totp, "TOTP MFA completion")

    print("step=complete_with_recovery")
    second = request_json(
        "POST",
        "/v1/auth/login",
        payload={"email": email, "password": password},
    )
    recovery_challenge = require_mfa_challenge(second, "recovery login")
    completed_recovery = request_json(
        "POST",
        "/v1/auth/mfa/complete",
        payload={
            "challenge_token": recovery_challenge,
            "code": recovery_codes[0],
        },
    )
    require_session(completed_recovery, "recovery MFA completion")

    print("step=recovery_replay_rejected")
    replay_login = request_json(
        "POST",
        "/v1/auth/login",
        payload={"email": email, "password": password},
    )
    replay_challenge = require_mfa_challenge(replay_login, "replay login")
    replay_code = expect_failure(
        "POST",
        "/v1/auth/mfa/complete",
        status=401,
        payload={
            "challenge_token": replay_challenge,
            "code": recovery_codes[0],
        },
    )
    if replay_code != "MFA_INVALID":
        raise AssertionError(f"unexpected recovery replay error: {replay_code}")

    print("step=bind_post_mfa_device")
    request_json(
        "POST",
        "/v1/devices/bind",
        payload=new_device_payload(),
        bearer=totp_session,
    )

    rotate_counter = wait_for_counter_after(login_counter)
    print("step=rotate_recovery_codes")
    rotated = request_json(
        "POST",
        "/v1/account/mfa/recovery-codes/rotate",
        payload={"code": totp(secret, rotate_counter)},
        bearer=totp_session,
    )
    if rotated.get("status") != "RECOVERY_CODES_ROTATED":
        raise AssertionError("recovery rotation status mismatch")
    rotated_codes = rotated.get("recovery_codes")
    if not isinstance(rotated_codes, list) or len(rotated_codes) != 10:
        raise AssertionError("expected 10 rotated recovery codes")

    print("step=security_state_enabled")
    enabled_state = request_json(
        "GET",
        "/v1/account/security",
        bearer=totp_session,
    )
    if enabled_state.get("mfa_enabled") is not True:
        raise AssertionError("security state did not report MFA enabled")
    if enabled_state.get("mfa_recovery_codes_remaining") != 10:
        raise AssertionError("rotated recovery-code count mismatch")

    print("step=provider_catalog")
    providers = request_json("GET", "/v1/auth/providers").get("providers", [])
    enabled_providers = sorted(
        str(item.get("provider"))
        for item in providers
        if isinstance(item, dict) and item.get("enabled") is True
    )
    print("enabled_federated_providers=" + (",".join(enabled_providers) or "none"))

    print("step=disable_mfa")
    disabled = request_json(
        "POST",
        "/v1/account/mfa/totp/disable",
        payload={"code": rotated_codes[0]},
        bearer=totp_session,
    )
    if disabled.get("status") != "MFA_DISABLED":
        raise AssertionError("MFA disable status mismatch")

    print("step=disable_revokes_session")
    expect_failure(
        "GET",
        "/v1/account/security",
        status=401,
        bearer=totp_session,
    )

    print("step=password_only_after_disable")
    final_login = request_json(
        "POST",
        "/v1/auth/login",
        payload={"email": email, "password": password},
    )
    require_session(final_login, "post-disable password login")
    if final_login.get("mfa_required") is True:
        raise AssertionError("post-disable login still requires MFA")

    print("STAGING_MFA_ACCEPTANCE=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApiFailure as exc:
        print(f"STAGING_MFA_ACCEPTANCE=FAIL http_status={exc.status} code={exc.code}")
        raise
    except Exception as exc:
        print(f"STAGING_MFA_ACCEPTANCE=FAIL type={type(exc).__name__}")
        raise
