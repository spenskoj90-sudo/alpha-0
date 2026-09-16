from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

_SERVICE_ROLE_SQL = "SELECT set_config('app.service_role', 'true', true)"
_BOUNDARY_MARKER = "_sentinel_transaction_service_role"


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

    @event.listens_for(engine, "begin")
    def _set_service_role(connection) -> None:  # type: ignore[no-untyped-def]
        connection.exec_driver_sql(_SERVICE_ROLE_SQL)

    setattr(engine, _BOUNDARY_MARKER, True)
    return engine


def create_service_role_engine(database_url: str, **kwargs: Any) -> Engine:
    """Create a PostgreSQL engine with the transaction-local RLS boundary."""

    return install_transaction_service_role(create_engine(database_url, **kwargs))
