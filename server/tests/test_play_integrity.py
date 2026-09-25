from __future__ import annotations

import time

from app.core.integrity import (
    IntegrityNonceStore,
    IntegrityTier,
    PlayIntegrityVerifier,
    authorize_for_tier,
    classify_verdicts,
)


def _payload(
    *,
    nonce: str,
    package: str = "com.alpha0.app",
    cert: str = "2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
    verdicts: list[str] | None = None,
    ts_ms: int | None = None,
    app_verdict: str = "PLAY_RECOGNIZED",
) -> dict:
    return {
        "tokenPayloadExternal": {
            "requestDetails": {
                "requestPackageName": package,
                "nonce": nonce,
                "timestampMillis": str(ts_ms if ts_ms is not None else int(time.time() * 1000)),
            },
            "appIntegrity": {
                "appRecognitionVerdict": app_verdict,
                "packageName": package,
                "certificateSha256Digest": [cert],
            },
            "deviceIntegrity": {
                "deviceRecognitionVerdict": verdicts if verdicts is not None else ["MEETS_STRONG_INTEGRITY", "MEETS_DEVICE_INTEGRITY", "MEETS_BASIC_INTEGRITY"]
            },
        }
    }


def test_classify_and_authorize_tiers():
    assert classify_verdicts({"MEETS_STRONG_INTEGRITY"}) is IntegrityTier.STRONG
    assert authorize_for_tier(IntegrityTier.STRONG, "device:rotate") is True
    assert authorize_for_tier(IntegrityTier.DEVICE, "device:rotate") is False
    assert authorize_for_tier(IntegrityTier.BASIC, "game:read") is True
    assert authorize_for_tier(IntegrityTier.UNKNOWN, "game:read") is False


def test_nonce_one_time_and_expired():
    store = IntegrityNonceStore(ttl_seconds=60)
    nonce = store.issue()
    assert store.consume(nonce) is True
    assert store.consume(nonce) is False
    assert store.consume("") is False


def test_verifier_fail_closed_without_audience():
    v = PlayIntegrityVerifier(audience="", decoder=lambda t: _payload(nonce="x"))
    result = v.verify("token", "x")
    assert result.trusted is False
    assert result.reason == "PLAY_INTEGRITY_NOT_CONFIGURED"
    assert result.tier is IntegrityTier.UNKNOWN


def test_verifier_valid_token():
    nonce = "server-nonce-1"

    def decoder(token: str):
        assert token == "good-token"
        return _payload(nonce=nonce)

    v = PlayIntegrityVerifier(
        audience="123456789",
        package_name="com.alpha0.app",
        cert_digest="2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E",
        decoder=decoder,
    )
    result = v.verify("good-token", nonce)
    assert result.trusted is True
    assert result.tier is IntegrityTier.STRONG
    assert result.reason == "PLAY_INTEGRITY_VERIFIED"


def test_verifier_wrong_nonce():
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: _payload(nonce="other"),
    )
    result = v.verify("tok", "expected")
    assert result.trusted is False
    assert result.reason == "INTEGRITY_NONCE_MISMATCH"


def test_verifier_wrong_package():
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: _payload(nonce="n", package="com.evil.app"),
    )
    result = v.verify("tok", "n")
    assert result.reason == "INTEGRITY_PACKAGE_MISMATCH"
    assert result.trusted is False


def test_verifier_wrong_certificate():
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        decoder=lambda t: _payload(nonce="n"),
    )
    result = v.verify("tok", "n")
    assert result.reason == "INTEGRITY_CERTIFICATE_MISMATCH"


def test_verifier_stale_token():
    old = int((time.time() - 10_000) * 1000)
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: _payload(nonce="n", ts_ms=old),
        max_token_age_seconds=300,
    )
    result = v.verify("tok", "n")
    assert result.reason == "INTEGRITY_TOKEN_STALE"


def test_verifier_insufficient_device():
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: _payload(nonce="n", verdicts=[]),
    )
    result = v.verify("tok", "n")
    assert result.trusted is False
    assert result.reason == "INTEGRITY_DEVICE_INSUFFICIENT"


def test_verifier_malformed_and_missing_token():
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: (_ for _ in ()).throw(ValueError("bad")),
    )
    assert v.verify("", "n").reason == "INTEGRITY_TOKEN_REQUIRED"
    assert v.verify("x" * 10, "n").reason == "INTEGRITY_TOKEN_INVALID"


def test_client_verdicts_cannot_raise_tier_via_verifier():
    """Even if a decoder returned empty device verdicts, client lists are not consulted."""
    v = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=lambda t: _payload(nonce="n", verdicts=["MEETS_BASIC_INTEGRITY"]),
    )
    result = v.verify("tok", "n")
    assert result.tier is IntegrityTier.BASIC
    assert result.trusted is True



def test_classify_verdicts_covers_device_basic_unknown_and_failed():
    assert classify_verdicts({"MEETS_DEVICE_INTEGRITY"}) is IntegrityTier.DEVICE
    assert classify_verdicts({"MEETS_BASIC_INTEGRITY"}) is IntegrityTier.BASIC
    assert classify_verdicts(set()) is IntegrityTier.UNKNOWN
    assert classify_verdicts({"UNEVALUATED"}) is IntegrityTier.FAILED
    assert authorize_for_tier(IntegrityTier.DEVICE, "game:read") is True
    assert authorize_for_tier(IntegrityTier.BASIC, "device:rotate") is False
    assert authorize_for_tier(IntegrityTier.FAILED, "game:read") is False


def test_nonce_store_rejects_expired_nonce_without_marking_it_used():
    store = IntegrityNonceStore(ttl_seconds=60)
    nonce = store.issue()
    digest = __import__("hashlib").sha256(nonce.encode("utf-8")).hexdigest()
    store._nonces[digest]["expires_at"] = time.time() - 1
    assert store.consume(nonce) is False
    assert store._nonces[digest]["used"] is False


def _configured(decoder):
    return PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        decoder=decoder,
    )


def test_verifier_rejects_nonstr_token_oversize_and_missing_package():
    verifier = _configured(lambda _t: _payload(nonce="n"))
    assert verifier.verify(None, "n").reason == "INTEGRITY_TOKEN_REQUIRED"
    assert verifier.verify("x" * 65537, "n").reason == "INTEGRITY_TOKEN_MALFORMED"

    def missing_package(_token):
        payload = _payload(nonce="n")
        details = payload["tokenPayloadExternal"]["requestDetails"]
        details.pop("requestPackageName")
        payload["tokenPayloadExternal"]["appIntegrity"].pop("packageName")
        return payload

    result = _configured(missing_package).verify("tok", "n")
    assert result.reason == "INTEGRITY_PACKAGE_MISSING"
    assert result.trusted is False


def test_verifier_accepts_top_level_payload_and_string_certificate_digest():
    nonce = "n"
    payload = _payload(nonce=nonce)["tokenPayloadExternal"]
    payload["appIntegrity"]["certificateSha256Digest"] = (
        "2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E"
    )
    # Exercise requestPackageName fallback to appIntegrity.packageName.
    payload["requestDetails"].pop("requestPackageName")
    result = _configured(lambda _t: payload).verify("tok", nonce)
    assert result.trusted is True
    assert result.package_name == "com.alpha0.app"


def test_verifier_rejects_empty_certificate_future_and_malformed_timestamps():
    def empty_cert(_token):
        return _payload(nonce="n", cert="")

    assert _configured(empty_cert).verify("tok", "n").reason == "INTEGRITY_CERTIFICATE_MISMATCH"

    future = int((time.time() + 120) * 1000)
    assert _configured(lambda _t: _payload(nonce="n", ts_ms=future)).verify("tok", "n").reason == "INTEGRITY_TOKEN_STALE"

    def malformed_time(_token):
        payload = _payload(nonce="n")
        payload["tokenPayloadExternal"]["requestDetails"]["timestampMillis"] = "not-a-number"
        return payload

    assert _configured(malformed_time).verify("tok", "n").reason == "INTEGRITY_TOKEN_MALFORMED"


def test_verifier_rejects_unrecognized_app_and_failed_device_verdict():
    unrecognized = _configured(
        lambda _t: _payload(nonce="n", app_verdict="UNEVALUATED")
    ).verify("tok", "n")
    assert unrecognized.reason == "INTEGRITY_APP_UNEVALUATED"
    assert unrecognized.trusted is False

    failed = _configured(
        lambda _t: _payload(nonce="n", verdicts=["MEETS_VIRTUAL_INTEGRITY"])
    ).verify("tok", "n")
    assert failed.tier is IntegrityTier.FAILED
    assert failed.reason == "INTEGRITY_DEVICE_INSUFFICIENT"


def test_decode_without_decoder_or_access_token_fails_closed():
    verifier = PlayIntegrityVerifier(
        audience="1",
        package_name="com.alpha0.app",
        cert_digest="2ACD1CFFF4F34DB1250D3F6C81F0887493C4602D3CFA65310993C058089DB88E",
        access_token="",
    )
    result = verifier.verify("tok", "n")
    assert result.reason == "INTEGRITY_TOKEN_INVALID"
    assert result.trusted is False
