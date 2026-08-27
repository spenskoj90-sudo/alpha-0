from concurrent.futures import ThreadPoolExecutor
import os

import pytest

from app.core.store import MemoryStore, PostgresStore


def test_memory_store_refresh_rotation_revokes_previous_access_session():
    store = MemoryStore()
    old_access, old_refresh, _, _ = store.issue_session("device-1", "user-1", 3600, 7200)

    rotated = store.rotate_refresh(old_refresh, 3600, 7200)

    assert rotated is not None
    new_access, new_refresh, _, _, old_record = rotated
    assert new_access != old_access
    assert new_refresh != old_refresh
    assert old_record["refresh_used"] is True
    assert old_record["revoked"] is True
    assert store.get_session(old_access) is None
    assert store.get_session(new_access) is not None

    # One-time refresh rotation remains enforced after the old session is revoked.
    assert store.rotate_refresh(old_refresh, 3600, 7200) is None


def test_concurrent_refresh_does_not_issue_multiple_valid_pairs():
    store = MemoryStore()
    old_access, old_refresh, _, _ = store.issue_session("device-1", "user-1", 3600, 7200)

    def attempt(_):
        return store.rotate_refresh(old_refresh, 3600, 7200)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    successes = [item for item in results if item is not None]
    assert len(successes) == 1
    new_access = successes[0][0]
    assert store.get_session(old_access) is None
    assert store.get_session(new_access) is not None
    assert store.rotate_refresh(old_refresh, 3600, 7200) is None


@pytest.mark.postgres
def test_postgres_concurrent_refresh_does_not_issue_multiple_valid_pairs():
    """Race proof for production store: one refresh token cannot mint multiple pairs."""
    database_url = os.environ["DATABASE_URL"]
    store = PostgresStore(database_url)
    device_id = store.register_device(
        "pg-refresh-race",
        "android",
        "cHVibGlj",
        "b" * 64,
        "challenge-pg-refresh",
    )
    old_access, old_refresh, _, _ = store.issue_session(device_id, "pg-refresh-race", 3600, 7200)
    assert store.get_session(old_access) is not None

    def attempt(_):
        return store.rotate_refresh(old_refresh, 3600, 7200)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    successes = [item for item in results if item is not None]
    assert len(successes) == 1, f"expected 1 success, got {len(successes)}"
    new_access = successes[0][0]
    assert store.get_session(old_access) is None
    assert store.get_session(new_access) is not None
    assert store.rotate_refresh(old_refresh, 3600, 7200) is None
    store.engine.dispose()
