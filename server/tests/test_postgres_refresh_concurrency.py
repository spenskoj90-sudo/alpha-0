from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def _ensure_identity(store, user_id: str) -> None:
    with store.engine.begin() as conn:
        conn.execute(text("INSERT INTO identities(user_handle) VALUES (:u) ON CONFLICT (user_handle) DO NOTHING"), {"u": user_id})


def test_postgres_refresh_rotation_is_single_winner_under_concurrency():
    from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, store
    from app.core.store import PostgresStore
    from app.core.security import session_hash

    assert isinstance(store, PostgresStore)
    user_id = "pg-refresh-concurrency"
    _ensure_identity(store, user_id)
    _, refresh_token, _, _ = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)

    def rotate():
        return store.rotate_refresh(refresh_token, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: rotate(), range(8)))

    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    winner_access, winner_refresh, _, _, old_session = winners[0]
    assert winner_access
    assert winner_refresh
    assert old_session["user_id"] == user_id

    assert store.rotate_refresh(refresh_token, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS) is None

    with store.engine.connect() as conn:
        row = conn.execute(text("SELECT refresh_used_at, revoked_at FROM sessions WHERE refresh_token_hash = :rh"), {"rh": session_hash(refresh_token)}).mappings().one()
    assert row["refresh_used_at"] is not None
    assert row["revoked_at"] is not None

    with store.engine.connect() as conn:
        replacement_count = conn.execute(text("SELECT COUNT(*) FROM sessions WHERE identity_id = (SELECT id FROM identities WHERE user_handle = :u) AND refresh_token_hash <> :rh"), {"u": user_id, "rh": session_hash(refresh_token)}).scalar_one()
    assert replacement_count == 1
