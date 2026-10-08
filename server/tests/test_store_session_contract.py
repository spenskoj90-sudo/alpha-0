from concurrent.futures import ThreadPoolExecutor
import os
import uuid

import pytest
from sqlalchemy import event, text

from app.core.security import session_hash
from app.core.store import MemoryStore, PostgresStore
from app.core.user_store import UserAccountStore


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
def test_generic_refresh_cannot_escape_web_family_or_consume_its_one_use_proof(backend):
    store = backend(os.environ['DATABASE_URL']) if backend is PostgresStore else backend()
    suffix = uuid.uuid4().hex
    family = 'bound-refresh-' + suffix + 'x' * 24
    user = 'bound-refresh-' + suffix
    try:
        store.register_device(user, 'android', 'bound-key-' + suffix, (suffix * 2)[:64], 'bound-challenge-' + suffix)
        operation = store.begin_web_session_operation(family)
        access, refresh, _, _ = store.issue_web_session(None, user, 3600, 7200, family, operation)
        assert store.rotate_refresh(refresh, 3600, 7200) is None
        assert store.get_session(access) is not None
        next_operation = store.begin_web_session_operation(family, create=False, refresh_token=refresh)
        rotated = store.rotate_web_refresh(refresh, 3600, 7200, family, next_operation)
        assert rotated is not None
        assert store.rotate_refresh(rotated[1], 3600, 7200) is None
        logout = store.begin_web_session_operation(family, create=False, revocation=True)
        assert store.revoke_web_session_family(family, logout)
        assert store.get_session(rotated[0]) is None
        assert store.rotate_refresh(rotated[1], 3600, 7200) is None
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
def test_atomic_reset_fences_a_login_authenticated_before_reset_even_after_a_failed_attempt(backend):
    database = os.environ['DATABASE_URL'] if backend is PostgresStore else None
    store = backend(database) if database else backend()
    accounts = UserAccountStore(database)
    suffix = uuid.uuid4().hex
    email = 'reset-auth-race-' + suffix + '@example.com'
    old_password, new_password = 'Reset-race-before-password-123', 'Reset-race-after-password-456'
    family = 'reset-auth-family-' + suffix + 'x' * 24
    try:
        accounts.register(email, old_password)
        original = store.begin_web_session_operation(family)
        access = store.issue_web_session(None, email, 3600, 7200, family, original)[0]
        pending = store.begin_web_session_operation(family, create=False)
        assert accounts.authenticate(email, old_password) == email
        code = accounts.issue_action_code(email, 'PASSWORD_RESET')
        def unavailable(conn):
            raise RuntimeError('TOMBSTONE_UNAVAILABLE')
        with pytest.raises(RuntimeError, match='TOMBSTONE_UNAVAILABLE'):
            accounts.reset_password(code, new_password, store, email, before_commit=unavailable)
        assert accounts.authenticate(email, old_password) == email
        assert store.get_session(access) is not None
        def fence(conn):
            store.revoke_web_session_family_latest(family, connection=conn)
        assert accounts.reset_password(code, new_password, store, email, before_commit=fence) == email
        # Resume the pending old-password login after the successful commit.
        assert store.issue_web_session(None, email, 3600, 7200, family, pending) is None
        assert store.get_session(access) is None
        assert accounts.authenticate(email, old_password) is None
        assert accounts.authenticate(email, new_password) == email
        assert accounts.reset_password(code, new_password, store, email, before_commit=fence) is None
    finally:
        if database:
            store.engine.dispose()
            accounts._engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
@pytest.mark.parametrize("proof_state", ["missing", "expired", "revoked", "device", "other-family"])
def test_unknown_family_cannot_allocate_with_untrusted_access_proof(backend, proof_state):
    store = backend(os.environ["DATABASE_URL"]) if backend is PostgresStore else backend()
    suffix = uuid.uuid4().hex
    user = "invalid-access-" + suffix
    family = "invalid-access-family-" + suffix + "x" * 24
    try:
        device = store.register_device(user, "android", "invalid-access-key-" + suffix, (suffix * 2)[:64], "invalid-access-challenge-" + suffix)
        if proof_state == 'other-family':
            other = 'other-access-family-' + suffix + 'y' * 24
            operation = store.begin_web_session_operation(other)
            access, _, _, _ = store.issue_web_session(None, user, 3600, 7200, other, operation)
        else:
            access, _, _, _ = store.issue_session(device if proof_state == 'device' else None, user,
                                                 -1 if proof_state == 'expired' else 3600, 7200)
            if proof_state == 'revoked':
                store.revoke_session(access)
            if proof_state == 'missing':
                access = 'unknown-access-proof'
        assert store.begin_web_session_operation(family, create=False, access_token=access, revocation=True) is None
        if isinstance(store, MemoryStore):
            assert session_hash(family) not in store.web_session_families
        else:
            with store.engine.begin() as conn:
                assert conn.execute(text('SELECT 1 FROM web_session_families WHERE family_hash=:family'), {'family': session_hash(family)}).first() is None
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
@pytest.mark.parametrize("refresh_state", ["expired", "consumed"])
def test_live_legacy_access_retires_expired_refresh_once_without_revoking_other_browser(backend, refresh_state):
    store = backend(os.environ["DATABASE_URL"]) if backend is PostgresStore else backend()
    suffix = uuid.uuid4().hex
    user = "stale-legacy-access-" + suffix
    try:
        store.register_device(user, "android", "access-proof-" + suffix, (suffix * 2)[:64], "access-challenge-" + suffix)
        access, refresh, _, _ = store.issue_session(None, user, 3600, -1 if refresh_state == "expired" else 7200)
        if refresh_state == "consumed":
            access = store.rotate_refresh(refresh, 3600, 7200)[0]
        independent, _, _, _ = store.issue_session(None, user, 3600, 7200)
        family = "access-retirement-" + suffix + "x" * 24
        operation = store.begin_web_session_operation(family, create=False, refresh_token=refresh,
                                                     access_token=access, revocation=True)
        assert operation == 1
        assert store.revoke_web_session_family(family, operation, refresh)
        assert store.get_session(access) is None
        assert store.get_session(independent) is not None
        assert store.begin_web_session_operation("replay-access-" + suffix + "y" * 24, create=False,
                                                refresh_token=refresh, access_token=access, revocation=True) is None
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
def test_logout_during_registration_hashing_does_not_persist_an_orphan_account(backend, monkeypatch):
    from app.core import user_store as accounts_module
    database = os.environ["DATABASE_URL"] if backend is PostgresStore else None
    store = backend(database) if database else backend()
    accounts = UserAccountStore(database)
    suffix = uuid.uuid4().hex
    email = f"atomic-registration-{suffix}@example.com"
    password = "Atomic-registration-password-123"
    family = "atomic-registration-" + suffix + "x" * 24
    operation = store.begin_web_session_operation(family)
    original_hash = accounts_module.hash_password
    def logout_during_hash(value):
        hashed = original_hash(value)
        logout = store.begin_web_session_operation(family, create=False, revocation=True)
        assert store.revoke_web_session_family(family, logout)
        return hashed
    monkeypatch.setattr(accounts_module, "hash_password", logout_during_hash)
    try:
        assert accounts.register_web_session(email, password, store, 3600, 7200, family, operation) is None
        assert accounts.authenticate(email, password) is None
        monkeypatch.setattr(accounts_module, "hash_password", original_hash)
        operation = store.begin_web_session_operation(family)
        assert accounts.register_web_session(email, password, store, 3600, 7200, family, operation) is not None
        assert accounts.authenticate(email, password) == email
    finally:
        if database:
            accounts._engine.dispose()
            store.engine.dispose()


@pytest.mark.postgres
def test_registration_account_and_generation_roll_back_when_session_insert_fails():
    database = os.environ["DATABASE_URL"]
    store = PostgresStore(database)
    accounts = UserAccountStore(database)
    suffix = uuid.uuid4().hex
    email = f"registration-rollback-{suffix}@example.com"
    password = "Registration-rollback-password-123"
    family = "registration-rollback-" + suffix + "x" * 24
    operation = store.begin_web_session_operation(family)
    def fail_session_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("INSERT INTO sessions("):
            raise RuntimeError("SESSION_INSERT_UNAVAILABLE")
    event.listen(store.engine, "before_cursor_execute", fail_session_insert)
    try:
        with pytest.raises(RuntimeError, match="SESSION_INSERT_UNAVAILABLE"):
            accounts.register_web_session(email, password, store, 3600, 7200, family, operation)
        assert accounts.authenticate(email, password) is None
        with store.engine.begin() as conn:
            assert conn.execute(text("SELECT 1 FROM identities WHERE user_handle=:email"), {"email": email}).first() is None
            assert conn.execute(text("SELECT active_generation FROM web_session_families WHERE family_hash=:family"),
                                {"family": session_hash(family)}).scalar_one() == 0
        event.remove(store.engine, "before_cursor_execute", fail_session_insert)
        assert accounts.register_web_session(email, password, store, 3600, 7200, family, operation) is not None
        assert accounts.authenticate(email, password) == email
    finally:
        if event.contains(store.engine, "before_cursor_execute", fail_session_insert):
            event.remove(store.engine, "before_cursor_execute", fail_session_insert)
        accounts._engine.dispose()
        store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
def test_migration_reservation_is_fenced_by_the_acknowledged_retirement_generation(backend):
    store = backend(os.environ["DATABASE_URL"]) if backend is PostgresStore else backend()
    family = "migration-fence-" + uuid.uuid4().hex + "x" * 24
    try:
        with pytest.raises(ValueError, match="WEB_SESSION_SUPERSEDED"):
            store.begin_web_session_operation(family, expected_generation=1)
        retired = store.begin_web_session_operation(family)
        assert store.revoke_web_session_family(family, retired)
        continuation = store.begin_web_session_operation(family, expected_generation=retired)
        assert continuation == retired + 1
        store.cancel_web_session_operation(family, continuation)
        # Even an intervening uncommitted/cancelled request supersedes the old
        # continuation. A successful logout must also survive its delayed retry.
        with pytest.raises(ValueError, match="WEB_SESSION_SUPERSEDED"):
            store.begin_web_session_operation(family, expected_generation=retired)
        logout = store.begin_web_session_operation(family, create=False, revocation=True)
        assert store.revoke_web_session_family(family, logout)
        with pytest.raises(ValueError, match="WEB_SESSION_SUPERSEDED"):
            store.begin_web_session_operation(family, expected_generation=retired)
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
@pytest.mark.parametrize("proof_state", ["missing", "expired", "revoked", "device", "other-family"])
def test_unknown_web_family_rejects_unusable_or_device_bound_revocation_proof(backend, proof_state):
    store = backend(os.environ["DATABASE_URL"]) if backend is PostgresStore else backend()
    suffix = uuid.uuid4().hex
    family = "invalid-proof-" + suffix + "x" * 24
    user = "proof-user-" + suffix
    try:
        device = store.register_device(user, "android", "proof-key-" + suffix, (suffix * 2)[:64], "proof-challenge-" + suffix)
        if proof_state == "other-family":
            other_family = "other-proof-" + suffix + "y" * 24
            operation = store.begin_web_session_operation(other_family)
            _, refresh, _, _ = store.issue_web_session(None, user, 3600, 7200, other_family, operation)
        else:
            access, refresh, _, _ = store.issue_session(device if proof_state == "device" else None, user, 3600,
                                                       -1 if proof_state == "expired" else 7200)
            if proof_state == "revoked":
                store.revoke_session(access)
            if proof_state == "missing":
                refresh = "unknown-secret"
        assert store.begin_web_session_operation(family, create=False, refresh_token=refresh, revocation=True) is None
        if isinstance(store, MemoryStore):
            assert session_hash(family) not in store.web_session_families
        else:
            with store.engine.begin() as conn:
                assert conn.execute(text("SELECT 1 FROM web_session_families WHERE family_hash=:family"),
                                    {"family": session_hash(family)}).first() is None
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


@pytest.mark.parametrize("backend", [MemoryStore, pytest.param(PostgresStore, marks=pytest.mark.postgres)])
@pytest.mark.parametrize("proof_kind", ["refresh", "access"])
def test_concurrent_legacy_revocation_allocates_one_family_and_revokes_rotated_descendants(backend, proof_kind):
    store = backend(os.environ["DATABASE_URL"]) if backend is PostgresStore else backend()
    suffix = uuid.uuid4().hex
    user = "concurrent-legacy-" + suffix
    try:
        store.register_device(user, "android", "legacy-proof-" + suffix, (suffix * 2)[:64], "legacy-challenge-" + suffix)
        _, root_refresh, _, _ = store.issue_session(None, user, 3600, 7200)
        independent, _, _, _ = store.issue_session(None, user, 3600, 7200)
        rotated = store.rotate_refresh(root_refresh, 3600, 7200)
        assert rotated is not None

        def revoke_once(index):
            family = "concurrent-family-" + suffix + str(index)
            operation = store.begin_web_session_operation(family, create=False, refresh_token=root_refresh,
                access_token=rotated[0] if proof_kind == 'access' else None, revocation=True)
            if operation is not None:
                assert store.revoke_web_session_family(family, operation, root_refresh) is True
            return operation

        with ThreadPoolExecutor(max_workers=2) as pool:
            operations = list(pool.map(revoke_once, range(2)))
        assert sorted(item for item in operations if item is not None) == [1]
        assert store.get_session(rotated[0]) is None
        assert store.rotate_refresh(rotated[1], 3600, 7200) is None
        assert store.get_session(independent) is not None
    finally:
        if isinstance(store, PostgresStore):
            store.engine.dispose()


def test_web_operation_window_is_bounded_without_invalidating_active_session():
    store = MemoryStore()
    family = "bounded-family-" + "w" * 48
    operation = store.begin_web_session_operation(family)
    session = store.issue_web_session(None, "user-1", 3600, 7200, family, operation)
    for _ in range(256):
        cancelled = store.begin_web_session_operation(family)
        store.cancel_web_session_operation(family, cancelled)
    with pytest.raises(ValueError, match="WEB_SESSION_OPERATION_LIMIT"):
        store.begin_web_session_operation(family)
    assert len(store.web_session_families[session_hash(family)]["cancelled_operations"]) == 256
    assert store.get_session(session[0]) is not None
    logout = store.begin_web_session_operation(family, create=False, revocation=True)
    assert store.revoke_web_session_family(family, logout) is True
    assert store.get_session(session[0]) is None


def test_legacy_revocation_proof_can_allocate_only_one_family():
    store = MemoryStore()
    access, refresh, _, _ = store.issue_session(None, "legacy-user", 3600, 7200)
    family = "legacy-one-family-" + "q" * 48
    operation = store.begin_web_session_operation(family, create=False, refresh_token=refresh, revocation=True)
    assert operation == 1
    assert store.revoke_web_session_family(family, operation, refresh) is True
    assert store.get_session(access) is None
    assert store.begin_web_session_operation("other-family-" + "r" * 48,
        create=False, refresh_token=refresh, revocation=True) is None
    assert len(store.web_session_families) == 1


@pytest.mark.postgres
def test_postgres_web_allocations_and_cancellations_are_bounded():
    store = PostgresStore(os.environ["DATABASE_URL"])
    suffix = uuid.uuid4().hex
    family = "pg-bounded-" + suffix + "x" * 24
    try:
        assert store.begin_web_session_operation(family, create=False, revocation=True) is None
        assert store.begin_web_session_operation(family, create=False, refresh_token="invalid") is None
        with store.engine.begin() as conn:
            assert conn.execute(text("SELECT 1 FROM web_session_families WHERE family_hash=:family"),
                                {"family": session_hash(family)}).first() is None
        operation = store.begin_web_session_operation(family)
        store.cancel_web_session_operation(family, operation)
        for _ in range(255):
            operation = store.begin_web_session_operation(family)
            store.cancel_web_session_operation(family, operation)
        with pytest.raises(ValueError, match="WEB_SESSION_OPERATION_LIMIT"):
            store.begin_web_session_operation(family)
        logout = store.begin_web_session_operation(family, create=False, revocation=True)
        assert store.revoke_web_session_family(family, logout) is True
        with store.engine.begin() as conn:
            assert conn.execute(text("SELECT cardinality(cancelled_operations) FROM web_session_families "
                                     "WHERE family_hash=:family"), {"family": session_hash(family)}).scalar_one() == 0
        user = "pg-legacy-bounded-" + suffix
        store.register_device(user, "android", "legacy-key-" + suffix, (suffix * 2)[:64], "bounded-challenge-" + suffix)
        access, refresh, _, _ = store.issue_session(None, user, 3600, 7200)
        legacy_family = "pg-legacy-family-" + suffix + "q" * 24
        operation = store.begin_web_session_operation(legacy_family, create=False, refresh_token=refresh, revocation=True)
        assert operation == 1
        assert store.revoke_web_session_family(legacy_family, operation, refresh) is True
        assert store.get_session(access) is None
        assert store.begin_web_session_operation("pg-other-" + suffix + "r" * 24,
            create=False, refresh_token=refresh, revocation=True) is None
    finally:
        store.engine.dispose()


def test_memory_store_refresh_rotation_revokes_previous_access_session():
    store = MemoryStore()
    device_id = store.register_device("user-1", "android", "memory-refresh-key", "1" * 64, "challenge")
    old_access, old_refresh, _, _ = store.issue_session(device_id, "user-1", 3600, 7200)

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


def test_memory_web_session_generation_allows_pending_predecessor_then_revokes_it():
    store = MemoryStore()
    family = "browser-family-" + "a" * 48

    stale_operation = store.begin_web_session_operation(family)
    current_operation = store.begin_web_session_operation(family)

    stale = store.issue_web_session(
        None, "user-1", 3600, 7200, family, stale_operation
    )
    assert stale is not None
    assert store.get_session(stale[0]) is not None
    current = store.issue_web_session(
        None, "user-1", 3600, 7200, family, current_operation
    )
    assert current is not None
    current_access, current_refresh, _, _ = current
    assert store.get_session(stale[0]) is None
    assert store.get_session(current_access) is not None

    refresh_operation = store.begin_web_session_operation(family)
    logout_operation = store.begin_web_session_operation(family)
    assert store.revoke_web_session_family(family, logout_operation) is True

    assert store.rotate_web_refresh(
        current_refresh, 3600, 7200, family, refresh_operation
    ) is None
    assert store.get_session(current_access) is None


def test_memory_cancelled_later_web_operation_does_not_supersede_pending_success():
    store = MemoryStore()
    family = "browser-family-cancel-" + "b" * 48

    pending_success = store.begin_web_session_operation(family)
    failed_duplicate = store.begin_web_session_operation(family)

    issued = store.issue_web_session(
        None, "user-1", 3600, 7200, family, pending_success
    )
    assert issued is not None
    assert store.cancel_web_session_operation(family, failed_duplicate) is True
    assert store.get_session(issued[0]) is not None


def test_memory_earlier_commit_preserves_later_operation_cancellation():
    store = MemoryStore()
    family = "browser-family-cancelled-high-" + "c" * 48

    pending_success = store.begin_web_session_operation(family)
    cancelled_successor = store.begin_web_session_operation(family)
    assert store.cancel_web_session_operation(family, cancelled_successor) is True

    issued = store.issue_web_session(
        None, "user-1", 3600, 7200, family, pending_success
    )
    assert issued is not None
    assert store.issue_web_session(
        None, "user-1", 3600, 7200, family, cancelled_successor
    ) is None
    assert store.get_session(issued[0]) is not None


def test_memory_atomic_web_tombstone_revokes_family_and_legacy_refresh():
    store = MemoryStore()
    family = "browser-family-tombstone-" + "c" * 48
    operation = store.begin_web_session_operation(family)
    current = store.issue_web_session(None, "user-1", 3600, 7200, family, operation)
    assert current is not None
    legacy_access, legacy_refresh, _, _ = store.issue_session(None, "user-1", 3600, 7200)

    logout_operation = store.begin_web_session_operation(family)
    assert store.revoke_web_session_family(family, logout_operation, legacy_refresh) is True
    tombstone = store.revoke_web_session_family_latest(family)
    assert tombstone > logout_operation
    assert store.get_session(current[0]) is None
    assert store.get_session(legacy_access) is None
    assert store.rotate_refresh(legacy_refresh, 3600, 7200) is None


def test_memory_legacy_logout_revokes_only_presented_refresh_lineage():
    store = MemoryStore()
    user_id = "legacy-multi-browser-user"
    first_access, first_refresh, _, _ = store.issue_session(None, user_id, 3600, 7200)
    second_access, second_refresh, _, _ = store.issue_session(None, user_id, 3600, 7200)
    # Simulate rows created before migration 017 introduced explicit lineage.
    store.sessions[next(key for key, value in store.sessions.items() if value["refresh_hash"] == session_hash(first_refresh))].pop("refresh_lineage_hash", None)
    store.sessions[next(key for key, value in store.sessions.items() if value["refresh_hash"] == session_hash(second_refresh))].pop("refresh_lineage_hash", None)
    family = "legacy-lineage-family-" + "d" * 48
    operation = store.begin_web_session_operation(family)

    assert store.revoke_web_session_family(family, operation, first_refresh) is True
    assert store.get_session(first_access) is None
    assert store.rotate_refresh(first_refresh, 3600, 7200) is None
    assert store.get_session(second_access) is not None
    assert store.rotate_refresh(second_refresh, 3600, 7200) is not None


def test_concurrent_refresh_does_not_issue_multiple_valid_pairs():
    store = MemoryStore()
    device_id = store.register_device("user-1", "android", "memory-race-key", "2" * 64, "challenge")
    old_access, old_refresh, _, _ = store.issue_session(device_id, "user-1", 3600, 7200)

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

def test_memory_store_revoked_device_sessions_fail_closed_even_if_session_row_is_stale():
    store = MemoryStore()
    device_id = store.register_device("memory-revoke", "android", "memory-key", "9" * 64, "challenge")
    access, refresh, _, _ = store.issue_session(device_id, "memory-revoke", 3600, 7200)
    user_access, user_refresh, _, _ = store.issue_session(None, "memory-revoke", 3600, 7200)

    # Simulate historical/process-crash inconsistency: device state changed but
    # the session row itself was not marked revoked.
    store.devices[device_id]["state"] = "REVOKED"

    assert store.get_session(access) is None
    assert store.rotate_refresh(refresh, 3600, 7200) is None
    assert store.get_session(user_access) is not None
    assert store.rotate_refresh(user_refresh, 3600, 7200) is not None


@pytest.mark.postgres
def test_postgres_revoke_is_atomic_and_stale_device_sessions_fail_closed():
    store = PostgresStore(os.environ["DATABASE_URL"])
    suffix = uuid.uuid4().hex
    user_id = f"pg-revoke-{suffix}"
    device_id = store.register_device(
        user_id,
        "android",
        "cHVibGljLXJldm9rZS0" + suffix,
        ("7" + suffix * 2)[:64],
        "challenge-revoke",
    )
    first_access, first_refresh, _, _ = store.issue_session(device_id, user_id, 3600, 7200)
    second_access, _, _, _ = store.issue_session(device_id, user_id, 3600, 7200)
    user_access, user_refresh, _, _ = store.issue_session(None, user_id, 3600, 7200)

    assert store.revoke_device(device_id) is True
    assert store.get_device(device_id)["state"] == "REVOKED"
    assert store.get_session(first_access) is None
    assert store.get_session(second_access) is None
    assert store.rotate_refresh(first_refresh, 3600, 7200) is None
    assert store.revoke_device(device_id) is False

    # Revoking a device must not revoke independent least-privilege user sessions.
    assert store.get_session(user_access) is not None
    assert store.rotate_refresh(user_refresh, 3600, 7200) is not None

    # Defense-in-depth proof: even a deliberately stale/unrevoked session row
    # cannot authorize or rotate refresh once its device is REVOKED.
    stale_device = store.register_device(
        f"{user_id}-stale",
        "android",
        "cHVibGljLXN0YWxlLQ" + suffix,
        ("8" + suffix * 2)[:64],
        "challenge-stale",
    )
    stale_access, stale_refresh, _, _ = store.issue_session(stale_device, f"{user_id}-stale", 3600, 7200)
    with store.engine.begin() as conn:
        conn.execute(
            text("UPDATE device_bindings SET state='REVOKED',revoked_at=now() WHERE id=:id"),
            {"id": stale_device},
        )
    assert store.get_session(stale_access) is None
    assert store.rotate_refresh(stale_refresh, 3600, 7200) is None

    suspended_device = store.register_device(
        f"{user_id}-suspended",
        "android",
        "cHVibGljLXN1c3BlbmRlZC0" + suffix,
        ("6" + suffix * 2)[:64],
        "challenge-suspended",
    )
    with store.engine.begin() as conn:
        conn.execute(
            text("UPDATE device_bindings SET state='SUSPENDED' WHERE id=:id"),
            {"id": suspended_device},
        )
    assert store.revoke_device(suspended_device) is True
    assert store.get_device(suspended_device)["state"] == "REVOKED"
    assert store.revoke_device(suspended_device) is False
    store.engine.dispose()
