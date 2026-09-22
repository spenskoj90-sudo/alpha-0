from concurrent.futures import ThreadPoolExecutor
import os
import uuid

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


@pytest.mark.postgres
def test_postgres_device_rebind_is_idempotent_and_owner_scoped():
    store = PostgresStore(os.environ["DATABASE_URL"])
    suffix = uuid.uuid4().hex
    user_id = f"pg-rebind-{suffix}"
    fingerprint = (suffix * 2)[:64]
    public_key = "cHVibGljLXJlYmluZC0" + suffix

    first = store.register_device(
        user_id,
        "android",
        public_key,
        fingerprint,
        "challenge-first",
    )
    second = store.register_device(
        user_id,
        "android",
        public_key,
        fingerprint,
        "challenge-second",
    )

    assert second == first
    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.register_device(
            f"pg-rebind-foreign-{suffix}",
            "android",
            public_key,
            fingerprint,
            "challenge-foreign",
        )
    store.engine.dispose()

@pytest.mark.postgres
def test_postgres_device_rotation_is_atomic_and_conflict_rolls_back():
    store = PostgresStore(os.environ["DATABASE_URL"])
    suffix = uuid.uuid4().hex
    user_id = f"pg-rotate-{suffix}"
    old_fingerprint = ("a" + suffix * 2)[:64]
    old_key = "cHVibGljLW9sZC0" + suffix
    old_device = store.register_device(user_id, "android", old_key, old_fingerprint, "challenge-old")
    old_access, _, _, _ = store.issue_session(old_device, user_id, 3600, 7200)

    foreign_fingerprint = ("b" + suffix * 2)[:64]
    foreign_key = "cHVibGljLWZvcmVpZ24t" + suffix
    store.register_device(f"foreign-{suffix}", "android", foreign_key, foreign_fingerprint, "challenge-foreign")

    with pytest.raises(ValueError, match="DEVICE_KEY_CONFLICT"):
        store.rotate_device_identity(
            old_device,
            user_id,
            "android",
            foreign_key,
            foreign_fingerprint,
            "challenge-conflict",
            3600,
            7200,
        )
    assert store.get_device(old_device)["state"] == "ACTIVE"
    assert store.get_session(old_access) is not None

    new_fingerprint = ("c" + suffix * 2)[:64]
    new_key = "cHVibGljLW5ldy0" + suffix
    new_device, new_access, new_refresh, _, scopes = store.rotate_device_identity(
        old_device,
        user_id,
        "android",
        new_key,
        new_fingerprint,
        "challenge-new",
        3600,
        7200,
    )

    assert new_device != old_device
    assert new_access
    assert new_refresh
    assert "game:write" in scopes
    assert store.get_device(old_device)["state"] == "REVOKED"
    assert store.get_session(old_access) is None
    assert store.get_session(new_access)["device_id"] == new_device
    recovered = store.find_active_device_by_key(new_key, new_fingerprint)
    assert recovered is not None
    assert recovered["device_id"] == new_device

    with pytest.raises(ValueError, match="DEVICE_NOT_ACTIVE"):
        store.rotate_device_identity(
            old_device,
            user_id,
            "android",
            "cHVibGljLWFub3RoZXI",
            ("d" + suffix * 2)[:64],
            "challenge-retry",
            3600,
            7200,
        )
    store.engine.dispose()

@pytest.mark.postgres
def test_postgres_device_activity_metadata_is_truthful_and_throttled():
    store = PostgresStore(os.environ["DATABASE_URL"])
    suffix = uuid.uuid4().hex
    user_id = f"pg-seen-{suffix}"
    fingerprint = ("e" + suffix * 2)[:64]
    public_key = "cHVibGljLXNlZW4t" + suffix
    device_id = store.register_device(user_id, "android", public_key, fingerprint, "challenge-seen")

    initial = store.get_device(device_id)
    assert initial["created_at"] is not None
    assert initial["last_seen_at"] is None

    assert store.touch_device(device_id) is True
    first_seen = store.get_device(device_id)["last_seen_at"]
    assert first_seen is not None

    # Ordinary request volume cannot write last_seen_at on every call.
    assert store.touch_device(device_id) is False
    assert store.get_device(device_id)["last_seen_at"] == first_seen

    rotated_id, _, _, _, _ = store.rotate_device_identity(
        device_id,
        user_id,
        "android",
        "cHVibGljLXNlZW4tbmV3LQ" + suffix,
        ("f" + suffix * 2)[:64],
        "challenge-seen-new",
        3600,
        7200,
    )
    assert rotated_id != device_id
    assert store.get_device(device_id)["state"] == "REVOKED"
    assert store.touch_device(device_id) is False
    assert store.get_device(device_id)["last_seen_at"] == first_seen
    store.engine.dispose()

