import os

import psycopg
import pytest

from app.core.store import PostgresStore


@pytest.mark.postgres
def test_required_rls_policies_exist():
    database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    expected = {
        "identities": "identities_service_policy",
        "device_bindings": "device_bindings_service_policy",
        "sessions": "sessions_service_policy",
        "entitlements": "entitlements_service_policy",
        "characters": "characters_service_policy",
        "game_events": "game_events_service_policy",
        "audit_events": "audit_events_service_policy",
    }
    with psycopg.connect(database_url) as conn:
        for table, policy in expected.items():
            enabled, forced = conn.execute(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = %s::regclass",
                (table,),
            ).fetchone()
            assert enabled is True, table
            assert forced is True, table
            found = conn.execute("SELECT 1 FROM pg_policies WHERE tablename=%s AND policyname=%s", (table, policy)).fetchone()
            assert found == (1,), (table, policy)


@pytest.mark.postgres
def test_application_postgres_connections_opt_into_rls_service_policy():
    store = PostgresStore(os.environ["DATABASE_URL"])
    with store.engine.connect() as conn:
        assert conn.exec_driver_sql("SHOW app.service_role").scalar() == "true"
    store.engine.dispose()


@pytest.mark.postgres
def test_rls_denies_access_without_service_role():
    database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    store = PostgresStore(os.environ["DATABASE_URL"])
    device_id = store.register_device("rls-user-a", "android", "cHVibGlj", "a" * 64, "challenge-a")
    access, _, _, _ = store.issue_session(device_id, "rls-user-a", 3600, 7200)
    assert store.get_session(access) is not None
    with psycopg.connect(database_url) as conn:
        conn.execute("SELECT set_config('app.service_role', 'false', false)")
        sessions = conn.execute("SELECT count(*) FROM sessions").fetchone()[0]
        identities = conn.execute("SELECT count(*) FROM identities").fetchone()[0]
        entitlements = conn.execute("SELECT count(*) FROM entitlements").fetchone()[0]
        assert sessions == 0
        assert identities == 0
        assert entitlements == 0
        try:
            conn.execute("INSERT INTO identities(user_handle) VALUES (%s)", ("rls-user-b",))
            conn.commit()
        except Exception:
            conn.rollback()
        inserted = conn.execute("SELECT count(*) FROM identities WHERE user_handle=%s", ("rls-user-b",)).fetchone()[0]
        assert inserted == 0
    store.engine.dispose()
