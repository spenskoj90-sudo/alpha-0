"""Persisted email-code limits and atomic consumption across independent workers."""
from concurrent.futures import ThreadPoolExecutor
import os
import uuid

import pytest
from sqlalchemy import text

from app.core.retention import purge_expired_runtime_data
from app.core.user_store import UserAccountStore

pytestmark = pytest.mark.postgres


@pytest.fixture
def accounts():
    workers = [UserAccountStore(os.environ['DATABASE_URL']) for _ in range(2)]
    email = f'email-code-{uuid.uuid4().hex}@example.test'
    workers[0].register(email, 'Correct-test-password-123')
    try:
        yield workers, email
    finally:
        with workers[0]._engine.begin() as conn:
            conn.execute(text('DELETE FROM auth_action_tokens WHERE identity_id IN (SELECT identity_id FROM users WHERE email=:email)'), {'email': email})
            conn.execute(text('DELETE FROM users WHERE email=:email'), {'email': email})
            conn.execute(text('DELETE FROM identities WHERE user_handle=:email'), {'email': email})
        for worker in workers:
            worker._engine.dispose()


def test_postgres_consumption_is_atomic_across_workers(accounts):
    workers, email = accounts
    code = workers[0].issue_action_code(email, 'EMAIL_VERIFY')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda worker: worker.confirm_email(code, email), workers))
    assert sorted(results) == [False, True]
    assert not workers[1].confirm_email(code, email)


def test_postgres_attempts_and_request_budget_survive_restart_and_retention(accounts):
    workers, email = accounts
    first, restarted = workers
    code = first.issue_action_code(email, 'EMAIL_VERIFY')
    wrong = '11111111' if code != '11111111' else '22222222'
    for i in range(5):
        assert not workers[i % 2].confirm_email(wrong, email)
    assert not restarted.confirm_email(code, email)
    assert restarted.authenticate(email, 'Correct-test-password-123')
    # Expired short-lived challenges still count against the rolling issue budget.
    assert restarted.issue_action_code(email, 'EMAIL_VERIFY')
    assert first.issue_action_code(email, 'EMAIL_VERIFY')
    with first._engine.begin() as conn:
        conn.execute(text("UPDATE auth_action_tokens SET expires_at=now()-interval '1 second' WHERE identity_id IN (SELECT identity_id FROM users WHERE email=:email)"), {'email': email})
    purge_expired_runtime_data(first._engine, batch_size=100)
    assert restarted.issue_action_code(email, 'EMAIL_VERIFY') is None
    assert restarted.issue_action_code(email, 'PASSWORD_RESET')
    with first._engine.begin() as conn:
        conn.execute(text("UPDATE auth_action_tokens SET created_at=now()-interval '2 hours',expires_at=now()-interval '1 hour' WHERE identity_id IN (SELECT identity_id FROM users WHERE email=:email)"), {'email': email})
    purge_expired_runtime_data(first._engine, batch_size=100)
    assert restarted.issue_action_code(email, 'EMAIL_VERIFY')


def test_postgres_concurrent_issuance_cannot_exceed_account_budget(accounts):
    workers, email = accounts
    assert workers[0].issue_action_code(email, 'EMAIL_VERIFY')
    assert workers[1].issue_action_code(email, 'EMAIL_VERIFY')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda worker: worker.issue_action_code(email, 'EMAIL_VERIFY'), workers))
    assert sum(code is not None for code in results) == 1


def test_postgres_legacy_tokens_keep_their_original_contract(accounts):
    workers, email = accounts
    token = workers[0].issue_action_token(email, 'EMAIL_VERIFY', 86400)
    assert workers[1].confirm_email(token)
    assert not workers[0].confirm_email(token)
