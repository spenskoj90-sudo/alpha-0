from __future__ import annotations

import base64
import hashlib
import hmac
import time

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1


def decode_totp_secret(secret: str) -> bytes:
    normalized = "".join(secret.split()).replace("-", "").upper()
    if not normalized:
        raise ValueError("empty TOTP secret")
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    key = base64.b32decode(normalized + padding, casefold=True)
    if len(key) < 16:
        raise ValueError("TOTP secret must contain at least 128 bits")
    return key


def totp_at(key: bytes, counter: int) -> str:
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    dynamic = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{dynamic % (10 ** TOTP_DIGITS):0{TOTP_DIGITS}d}"


def matching_totp_counter(
    secret: str,
    code: str | None,
    *,
    now: float | None = None,
    last_counter: int | None = None,
    window: int = TOTP_WINDOW,
) -> int | None:
    provided = (code or "").strip()
    if len(provided) != TOTP_DIGITS or not provided.isdigit():
        return None
    try:
        key = decode_totp_secret(secret)
    except (ValueError, TypeError):
        return None
    current_counter = int((time.time() if now is None else now) // TOTP_STEP_SECONDS)
    for offset in range(-window, window + 1):
        counter = current_counter + offset
        if counter < 0:
            continue
        if last_counter is not None and counter <= last_counter:
            continue
        if hmac.compare_digest(provided, totp_at(key, counter)):
            return counter
    return None


def verify_totp(secret: str, code: str | None, *, now: float | None = None) -> bool:
    return matching_totp_counter(secret, code, now=now) is not None
