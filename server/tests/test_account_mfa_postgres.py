import hashlib
import os
import time
import uuid

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from app.core.account_mfa import AccountMfaService
from app.core.database_engine import create_service_role_engine
from app.core.totp import decode_totp_secret, totp_at
from app.core.user_store import UserAccountStore

pytestmark = pytest.mark.postgres


def _current_code(secret: str) -> str:
    return totp_at(decode_totp_secret(secret), int(time.time() // 30))


def test_postgres_account_mfa_lifecycle_hashing_and_attempt_cap(monkeypatch):
    database_url = os.environ["DATABASE_URL"]
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    accounts = UserAccountStore(database_url)
    mfa = AccountMfaService(database_url)
    probe = create_service_role_engine(database_url, pool_pre_ping=True)
    email = f"pg-mfa-{uuid.uuid4().hex}@example.com"

    try:
        user_id = accounts.register(email, "Correct-Horse-Battery-Staple-Postgres-MFA")
        enrollment = mfa.begin_enrollment(user_id, email)
        secret = enrollment["secret"]
        recovery = mfa.confirm_enrollment(user_id, _current_code(secret))
        assert recovery is not None
        assert len(recovery) == 10
        assert mfa.state(user_id) == {"enabled": True, "recovery_codes_remaining": 10}

        challenge = mfa.issue_login_challenge(user_id)
        assert challenge is not None
        raw_challenge, _ = challenge
        challenge_hash = hashlib.sha256(raw_challenge.encode()).hexdigest()

        with probe.begin() as conn:
            stored = conn.execute(
                text(
                    "SELECT m.secret_ciphertext,c.challenge_hash,c.attempt_count,c.consumed_at "
                    "FROM account_mfa_totp m "
                    "JOIN account_mfa_login_challenges c ON c.identity_id=m.identity_id "
                    "JOIN identities i ON i.id=m.identity_id "
                    "WHERE i.user_handle=:user_id AND c.challenge_hash=:challenge_hash"
                ),
                {"user_id": user_id, "challenge_hash": challenge_hash},
            ).mappings().one()
        assert secret not in stored["secret_ciphertext"]
        assert stored["challenge_hash"] == challenge_hash
        assert raw_challenge != stored["challenge_hash"]
        assert stored["attempt_count"] == 0
        assert stored["consumed_at"] is None

        for _ in range(8):
            assert mfa.complete_login_challenge(raw_challenge, "INVALID-RECOVERY-CODE") is None
        assert mfa.complete_login_challenge(raw_challenge, recovery[0]) is None

        with probe.begin() as conn:
            exhausted = conn.execute(
                text(
                    "SELECT attempt_count,consumed_at FROM account_mfa_login_challenges "
                    "WHERE challenge_hash=:challenge_hash"
                ),
                {"challenge_hash": challenge_hash},
            ).mappings().one()
        assert exhausted["attempt_count"] == 8
        assert exhausted["consumed_at"] is not None

        fresh = mfa.issue_login_challenge(user_id)
        assert fresh is not None
        assert mfa.complete_login_challenge(fresh[0], recovery[0]) == user_id
        assert mfa.state(user_id)["recovery_codes_remaining"] == 9
    finally:
        probe.dispose()
        if accounts._engine is not None:
            accounts._engine.dispose()
        if mfa._engine is not None:
            mfa._engine.dispose()


def _next_code(secret: str) -> str:
    return totp_at(decode_totp_secret(secret), int(time.time() // 30) + 1)


def test_postgres_account_mfa_recovery_rotation_and_disable_paths(monkeypatch):
    database_url = os.environ["DATABASE_URL"]
    monkeypatch.setenv("SENTINEL_ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    accounts = UserAccountStore(database_url)
    mfa = AccountMfaService(database_url)
    email = f"pg-mfa-rotate-{uuid.uuid4().hex}@example.com"

    try:
        user_id = accounts.register(email, "Correct-Horse-Battery-Staple-Postgres-MFA-Rotate")
        assert mfa.disable(user_id, "unused") is False
        assert mfa.rotate_recovery_codes(user_id, "000000") is None

        enrollment = mfa.begin_enrollment(user_id, email)
        secret = enrollment["secret"]
        first_recovery = mfa.confirm_enrollment(user_id, _current_code(secret))
        assert first_recovery is not None

        assert mfa.rotate_recovery_codes(user_id, "000000") is None
        rotated = mfa.rotate_recovery_codes(user_id, _next_code(secret))
        assert rotated is not None
        assert len(rotated) == 10
        assert set(rotated).isdisjoint(first_recovery)
        assert mfa.state(user_id)["recovery_codes_remaining"] == 10

        # Old recovery material was deleted by rotation.
        assert mfa.disable(user_id, first_recovery[0]) is False
        assert mfa.disable(user_id, rotated[0]) is True
        assert mfa.state(user_id) == {"enabled": False, "recovery_codes_remaining": 0}

        # Re-enrollment after disable is allowed and a fresh TOTP can disable.
        second = mfa.begin_enrollment(user_id, email)
        second_secret = second["secret"]
        second_recovery = mfa.confirm_enrollment(user_id, _current_code(second_secret))
        assert second_recovery is not None
        assert mfa.disable(user_id, _next_code(second_secret)) is True
        assert mfa.state(user_id)["enabled"] is False
    finally:
        if accounts._engine is not None:
            accounts._engine.dispose()
        if mfa._engine is not None:
            mfa._engine.dispose()
