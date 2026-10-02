from __future__ import annotations

from typing import Any
import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

_SERVICE_ROLE_SQL = "SELECT set_config('app.service_role', 'true', true)"
_BOUNDARY_MARKER = "_sentinel_transaction_service_role"
_RUNTIME_ROLE_SQL = """
SELECT r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
    OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid)
    OR EXISTS (SELECT 1 FROM pg_database WHERE datdba = r.oid)
    OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE c.relowner = r.oid AND n.nspname NOT LIKE 'pg_%'
                 AND n.nspname <> 'information_schema')
    OR has_database_privilege(current_database(), 'CREATE')
    OR has_schema_privilege('public', 'CREATE')
FROM pg_roles r WHERE r.rolname = current_user
"""


def restricted_database_role_required() -> bool:
    value = os.getenv("SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE", "false")
    if value not in {"true", "false"}:
        raise RuntimeError("SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE must be true or false")
    return value == "true"


def validate_runtime_database_role(connection: Any) -> None:
    # Effective privileges, not just FORCE RLS table flags. Never log a DSN.
    unsafe = connection.exec_driver_sql(_RUNTIME_ROLE_SQL).scalar_one()
    if unsafe is not False:
        raise RuntimeError("DATABASE_URL must use a restricted runtime role")


def install_transaction_service_role(engine: Engine) -> Engine:
    """Enable the RLS service role only for each SQLAlchemy transaction.

    The application deliberately avoids PostgreSQL startup parameters here.
    PgBouncer transaction-pooling endpoints can reject arbitrary startup GUCs,
    and a session-scoped setting could leak privilege between pooled clients.
    A transaction-local GUC preserves FORCE RLS while automatically resetting
    on commit/rollback.
    """

    if getattr(engine, _BOUNDARY_MARKER, False):
        return engine
    require_restricted_role = restricted_database_role_required()

    @event.listens_for(engine, "begin")
    def _set_service_role(connection) -> None:  # type: ignore[no-untyped-def]
        if require_restricted_role:
            validate_runtime_database_role(connection)
        connection.exec_driver_sql(_SERVICE_ROLE_SQL)

    setattr(engine, _BOUNDARY_MARKER, True)
    return engine


def create_service_role_engine(database_url: str, **kwargs: Any) -> Engine:
    """Create a PostgreSQL engine with the transaction-local RLS boundary."""

    return install_transaction_service_role(create_engine(database_url, **kwargs))
