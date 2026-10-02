import pytest

from app.core.database_engine import restricted_database_role_required, validate_runtime_database_role


@pytest.mark.parametrize('raw,expected', [(None, False), ('true', True), ('false', False)])
def test_restricted_role_configuration_is_explicit(monkeypatch, raw, expected):
    monkeypatch.delenv('SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE', raising=False)
    if raw is not None:
        monkeypatch.setenv('SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE', raw)
    assert restricted_database_role_required() is expected


@pytest.mark.parametrize('raw', ['', 'TRUE', 'yes', '0', 'invalid'])
def test_restricted_role_configuration_rejects_ambiguous_values(monkeypatch, raw):
    monkeypatch.setenv('SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE', raw)
    with pytest.raises(RuntimeError, match='must be true or false'):
        restricted_database_role_required()


@pytest.mark.postgres
def test_runtime_role_rejects_admin_and_checks_real_limited_role(monkeypatch):
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.exc import ProgrammingError
    from app.core.database_engine import create_service_role_engine

    monkeypatch.setenv('SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE', 'true')
    guarded = create_service_role_engine(os.environ['DATABASE_URL'])
    try:
        with pytest.raises(RuntimeError, match='restricted runtime role'):
            with guarded.begin():
                pass
    finally:
        guarded.dispose()

    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.connect() as conn:
            with pytest.raises(RuntimeError, match='restricted runtime role'):
                validate_runtime_database_role(conn)
            conn.rollback()
            transaction = conn.begin()
            conn.exec_driver_sql('CREATE ROLE sentinel_runtime_guard_probe NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS')
            conn.exec_driver_sql('GRANT USAGE ON SCHEMA public TO sentinel_runtime_guard_probe')
            conn.exec_driver_sql('GRANT SELECT ON identities TO sentinel_runtime_guard_probe')
            conn.exec_driver_sql('SET LOCAL ROLE sentinel_runtime_guard_probe')
            validate_runtime_database_role(conn)
            # RLS is actually applied without the application's transaction GUC.
            conn.exec_driver_sql("SELECT set_config('app.service_role', 'false', true)")
            assert conn.exec_driver_sql('SELECT count(*) FROM identities').scalar_one() == 0
            with pytest.raises(ProgrammingError) as denied:
                conn.exec_driver_sql('CREATE TABLE public.runtime_guard_must_not_exist (id integer)')
            assert denied.value.orig.sqlstate == '42501'
            transaction.rollback()
    finally:
        engine.dispose()
