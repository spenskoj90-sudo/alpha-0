from __future__ import annotations

import hashlib
import time

import pytest
from cryptography.fernet import Fernet

from app.core.account_mfa import AccountMfaConfigurationError, AccountMfaService
from app.core.totp import decode_totp_secret, matching_totp_counter, totp_at, verify_totp


def _code(secret: str, *, offset: int = 0) -> str:
    counter = int(time.time() // 30) + offset
    return totp_at(decode_totp_secret(secret), counter)


def test_totp_validation_rejects_malformed_secret_code_and_replay() -> None:
    assert matching_totp_counter("", "123456") is None
    assert matching_totp_counter("INVALID!", "123456") is None
    assert matching_totp_counter("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", None) is None
    assert matching_totp_counter("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", "abcdef") is None
    assert verify_totp("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", "000000", now=0) is False

    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    now = 1_800_000_000.0
    counter = int(now // 30)
    code = totp_at(decode_totp_secret(secret), counter)
    assert matching_totp_counter(secret, code, now=now) == counter
    assert matching_totp_counter(secret, code, now=now, last_counter=counter) is None


def test_mfa_cipher_fails_closed_on_missing_key_and_wrong_ciphertext(monkeypatch) -> None:
    service = AccountMfaService(None)
    monkeypatch.delenv("SENTINEL_ACCOUNT_MFA_KEY", raising=False)
    with pytest.raises(AccountMfaConfigurationError, match="ACCOUNT_MFA_KEY_NOT_CONFIGURED"):
        service._cipher()

    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    with pytest.raises(AccountMfaConfigurationError, match="ACCOUNT_MFA_SECRET_UNREADABLE"):
        service._decrypt_secret("not-a-valid-fernet-token")


def test_memory_mfa_enrollment_state_challenge_and_recovery_lifecycle(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    service = AccountMfaService(None)
    user = "mfa-boundary-user"

    assert service.state(user) == {"enabled": False, "recovery_codes_remaining": 0}
    assert service.issue_login_challenge(user) is None
    assert service.disable(user, "anything") is False
    assert service.rotate_recovery_codes(user, "anything") is None

    enrollment = service.begin_enrollment(user, "Owner+test@example.com")
    assert enrollment["secret"]
    assert enrollment["otpauth_uri"].startswith("otpauth://totp/SENTINEL%3AOwner%2Btest%40example.com?")
    assert "issuer=SENTINEL" in enrollment["otpauth_uri"]
    assert service.confirm_enrollment(user, "000000") is None

    code = _code(enrollment["secret"])
    recovery = service.confirm_enrollment(user, code)
    assert recovery is not None
    assert len(recovery) == 10
    assert len(set(recovery)) == 10
    assert service.confirm_enrollment(user, code) is None
    assert service.state(user) == {"enabled": True, "recovery_codes_remaining": 10}

    challenge = service.issue_login_challenge(user)
    assert challenge is not None
    token, _ = challenge
    digest = hashlib.sha256(token.encode()).hexdigest()
    assert token not in service._challenges
    assert digest in service._challenges

    assert service.complete_login_challenge("unknown-token", recovery[0]) is None
    assert service.complete_login_challenge(token, recovery[0]) == user
    assert service.complete_login_challenge(token, recovery[1]) is None
    assert service.state(user)["recovery_codes_remaining"] == 9

    assert service.disable(user, "wrong-code") is False
    assert service.disable(user, recovery[1]) is True
    assert service.state(user) == {"enabled": False, "recovery_codes_remaining": 0}
    assert digest not in service._challenges


def test_memory_mfa_expired_and_orphaned_challenges_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    service = AccountMfaService(None)
    user = "mfa-expiry-user"
    enrollment = service.begin_enrollment(user, user)
    recovery = service.confirm_enrollment(user, _code(enrollment["secret"]))
    assert recovery

    token, _ = service.issue_login_challenge(user)
    digest = service._digest(token)
    service._challenges[digest]["expires_at"] = service._challenges[digest]["expires_at"].replace(year=2000)
    assert service.complete_login_challenge(token, recovery[0]) is None

    fresh, _ = service.issue_login_challenge(user)
    fresh_digest = service._digest(fresh)
    service._memory[user]["enabled_at"] = None
    assert service.complete_login_challenge(fresh, recovery[0]) is None
    assert service._challenges[fresh_digest]["consumed_at"] is None


def test_memory_mfa_invalid_attempt_limit_consumes_challenge(monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    service = AccountMfaService(None)
    user = "mfa-attempt-limit"
    enrollment = service.begin_enrollment(user, user)
    recovery = service.confirm_enrollment(user, _code(enrollment["secret"]))
    assert recovery

    token, _ = service.issue_login_challenge(user)
    digest = service._digest(token)
    for _ in range(8):
        assert service.complete_login_challenge(token, "wrong") is None
    assert service._challenges[digest]["attempt_count"] == 8
    assert service._challenges[digest]["consumed_at"] is not None
    assert service.complete_login_challenge(token, recovery[0]) is None


def test_recovery_code_normalization_is_case_and_separator_insensitive() -> None:
    canonical = "ABCD-EFGH-IJKL"
    variant = "abcd efgh_ijkl"
    assert AccountMfaService._normalize_recovery_code(canonical) == "ABCDEFGHIJKL"
    assert AccountMfaService._recovery_digest(canonical) == AccountMfaService._recovery_digest(variant)
