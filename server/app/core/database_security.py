from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

_SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})
_LOCAL_DATABASE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})


def validate_database_url(database_url: str | None, environment: str) -> None:
    """Fail closed on plaintext remote PostgreSQL in production."""
    env = (environment or "development").strip().lower()
    if not database_url:
        if env == "production":
            raise RuntimeError("DATABASE_URL is required in production")
        return
    if env != "production":
        return

    normalized = re.sub(r"^postgresql\+[A-Za-z0-9_]+://", "postgresql://", database_url, count=1)
    parts = urlsplit(normalized)
    if parts.scheme not in {"postgresql", "postgres"} or not parts.hostname:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL in production")
    hostname = parts.hostname.lower()
    if hostname in _LOCAL_DATABASE_HOSTS:
        return
    query = parse_qs(parts.query, keep_blank_values=True)
    sslmode = (query.get("sslmode") or [""])[-1].lower()
    if sslmode not in _SECURE_SSL_MODES:
        raise RuntimeError("Remote production PostgreSQL requires sslmode=require, verify-ca, or verify-full")
