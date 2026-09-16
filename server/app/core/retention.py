from __future__ import annotations

import os
from collections.abc import Mapping

from sqlalchemy import Engine, text

DEFAULT_BATCH_SIZE = 1_000
MIN_BATCH_SIZE = 100
MAX_BATCH_SIZE = 10_000

# One transaction-scoped lock serializes a sweep across workers/replicas while still
# releasing automatically on commit/rollback or process loss.
RETENTION_ADVISORY_LOCK_ID = 7_153_000_012

# Operational/security transient data only. Durable audit, billing, game events,
# quality evidence, and user records are intentionally excluded here.
_PURGE_RULES: tuple[tuple[str, str], ...] = (
    ("idempotency_keys", "expires_at < now()"),
    ("device_challenges", "expires_at < now() - interval '1 hour' OR consumed_at < now() - interval '1 hour'"),
    ("proof_request_ids", "created_at < now() - interval '1 day'"),
    ("security_failures", "failed_at < now() - interval '1 day'"),
    (
        "sessions",
        "expires_at < now() - interval '7 days' AND "
        "(refresh_expires_at IS NULL OR refresh_expires_at < now() - interval '7 days')",
    ),
    ("outbox_events", "status IN ('DONE','FAILED') AND available_at < now() - interval '7 days'"),
    ("worker_jobs", "status IN ('DONE','FAILED') AND available_at < now() - interval '7 days'"),
)


def retention_batch_size_from_env(value: str | None = None) -> int:
    raw = value if value is not None else os.getenv("SENTINEL_RETENTION_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))
    try:
        batch_size = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("SENTINEL_RETENTION_BATCH_SIZE must be an integer") from exc
    if not MIN_BATCH_SIZE <= batch_size <= MAX_BATCH_SIZE:
        raise RuntimeError("SENTINEL_RETENTION_BATCH_SIZE is outside the allowed safety range")
    return batch_size


def purge_expired_runtime_data(engine: Engine, *, batch_size: int | None = None) -> Mapping[str, int]:
    """Delete one distributed-safe bounded batch of expired transient rows per table.

    A transaction-scoped PostgreSQL advisory lock makes concurrent workers/replicas
    collapse to one active sweep. Lock contention is a normal no-op and returns an
    empty mapping. Each rule uses a ctid-limited candidate set so one maintenance
    pass cannot turn into an unbounded delete or long-running lock storm.
    """
    limit = retention_batch_size_from_env() if batch_size is None else batch_size
    if not MIN_BATCH_SIZE <= limit <= MAX_BATCH_SIZE:
        raise ValueError("INVALID_RETENTION_BATCH_SIZE")

    deleted: dict[str, int] = {}
    with engine.begin() as conn:
        acquired = conn.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": RETENTION_ADVISORY_LOCK_ID},
        ).scalar_one()
        if acquired is not True:
            return {}

        for table_name, predicate in _PURGE_RULES:
            statement = text(
                f"WITH doomed AS ("
                f"SELECT ctid FROM {table_name} WHERE {predicate} LIMIT :limit"
                f") DELETE FROM {table_name} WHERE ctid IN (SELECT ctid FROM doomed)"
            )
            result = conn.execute(statement, {"limit": limit})
            deleted[table_name] = max(0, int(result.rowcount or 0))
    return deleted
