import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.postgres


def test_every_runtime_table_except_migration_metadata_has_forced_rls():
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                           count(p.policyname) AS policy_count
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    LEFT JOIN pg_policies p
                      ON p.schemaname = n.nspname AND p.tablename = c.relname
                    WHERE n.nspname = 'public' AND c.relkind = 'r'
                    GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity
                    ORDER BY c.relname
                    """
                )
            ).mappings().all()
    finally:
        engine.dispose()

    runtime = [row for row in rows if row["relname"] != "schema_migrations"]
    assert runtime
    assert all(row["relrowsecurity"] for row in runtime), runtime
    assert all(row["relforcerowsecurity"] for row in runtime), runtime
    assert all(row["policy_count"] >= 1 for row in runtime), runtime
