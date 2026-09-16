#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit

from sqlalchemy import create_engine

from app.core.database_security import validate_database_url
from app.core.retention import purge_expired_runtime_data, retention_batch_size_from_env


def _sqlalchemy_url(value: str) -> str:
    if re.match(r"^postgresql\+[A-Za-z0-9_]+://", value):
        return value
    if urlsplit(value).scheme in {"postgres", "postgresql"}:
        return re.sub(r"^(?:postgres|postgresql)://", "postgresql+psycopg://", value, count=1)
    return value


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    environment = os.getenv("SENTINEL_ENV", "production")
    validate_database_url(database_url, environment)
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    engine = create_engine(
        _sqlalchemy_url(database_url),
        pool_pre_ping=True,
        connect_args={"options": "-c app.service_role=true"},
    )
    try:
        deleted = purge_expired_runtime_data(engine, batch_size=retention_batch_size_from_env())
    finally:
        engine.dispose()
    print(json.dumps({"status": "ok", "deleted": deleted}, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
