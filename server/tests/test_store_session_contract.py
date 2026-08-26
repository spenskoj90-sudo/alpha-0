from app.core.store import MemoryStore


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
