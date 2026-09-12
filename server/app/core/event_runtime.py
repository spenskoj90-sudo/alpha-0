from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class ClaimedEvent:
    id: str
    event_type: str
    payload: dict[str, Any]
    attempts: int
    locked_by: str


class PostgresEventRuntime:
    """Lease-based outbox/worker runtime backed by durable PostgreSQL tables."""

    def __init__(
        self,
        database_url: str,
        *,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        backoff_base_seconds: int = 2,
    ):
        if lease_seconds <= 0 or max_attempts <= 0 or backoff_base_seconds <= 0:
            raise ValueError("INVALID_RUNTIME_LIMITS")
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"options": "-c app.service_role=true"},
        )
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.backoff_base_seconds = backoff_base_seconds

    @staticmethod
    def _token() -> str:
        return secrets.token_urlsafe(24)

    def claim_outbox(self, worker_id: str) -> ClaimedEvent | None:
        token = self._token()
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    WITH candidate AS (
                        SELECT id FROM outbox_events
                        WHERE (status = 'PENDING' AND available_at <= now())
                           OR (status = 'PROCESSING'
                               AND locked_until IS NOT NULL
                               AND locked_until <= now())
                        ORDER BY available_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE outbox_events o
                    SET status = 'PROCESSING',
                        attempts = o.attempts + 1,
                        locked_until = now() + (:lease_seconds * interval '1 second'),
                        locked_by = :locked_by
                    FROM candidate c
                    WHERE o.id = c.id
                    RETURNING o.id::text, o.event_type, o.payload_json,
                              o.attempts, o.locked_by
                    """
                ),
                {"lease_seconds": self.lease_seconds, "locked_by": token},
            ).mappings().first()
        if not row:
            return None
        return ClaimedEvent(
            row["id"],
            row["event_type"],
            dict(row["payload_json"]),
            row["attempts"],
            row["locked_by"],
        )

    def complete_outbox(self, event_id: str, locked_by: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE outbox_events
                    SET status = 'DONE', locked_until = NULL, locked_by = NULL
                    WHERE id = CAST(:id AS uuid)
                      AND status = 'PROCESSING'
                      AND locked_by = :locked_by
                    """
                ),
                {"id": event_id, "locked_by": locked_by},
            )
        return result.rowcount == 1

    def fail_outbox(
        self,
        event_id: str,
        locked_by: str,
        *,
        retry: bool = True,
        error: str | None = None,
    ) -> bool:
        del error
        with self.engine.begin() as conn:
            if retry:
                result = conn.execute(
                    text(
                        """
                        UPDATE outbox_events
                        SET status = CASE
                                WHEN attempts >= :max_attempts THEN 'FAILED'
                                ELSE 'PENDING'
                            END,
                            available_at = CASE
                                WHEN attempts >= :max_attempts THEN available_at
                                ELSE now() + (
                                    (:backoff_base * power(
                                        2, greatest(attempts - 1, 0)
                                    )) * interval '1 second'
                                )
                            END,
                            locked_until = NULL,
                            locked_by = NULL
                        WHERE id = CAST(:id AS uuid)
                          AND status = 'PROCESSING'
                          AND locked_by = :locked_by
                        """
                    ),
                    {
                        "id": event_id,
                        "locked_by": locked_by,
                        "max_attempts": self.max_attempts,
                        "backoff_base": self.backoff_base_seconds,
                    },
                )
            else:
                result = conn.execute(
                    text(
                        """
                        UPDATE outbox_events
                        SET status = 'FAILED', locked_until = NULL, locked_by = NULL
                        WHERE id = CAST(:id AS uuid)
                          AND status = 'PROCESSING'
                          AND locked_by = :locked_by
                        """
                    ),
                    {"id": event_id, "locked_by": locked_by},
                )
        return result.rowcount == 1

    def replay_failed_outbox(self, event_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE outbox_events
                    SET status = 'PENDING', attempts = 0, available_at = now(),
                        locked_until = NULL, locked_by = NULL
                    WHERE id = CAST(:id AS uuid) AND status = 'FAILED'
                    """
                ),
                {"id": event_id},
            )
        return result.rowcount == 1

    def claim_worker_job(self, worker_id: str) -> dict[str, Any] | None:
        token = self._token()
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    WITH candidate AS (
                        SELECT id FROM worker_jobs
                        WHERE (status = 'PENDING' AND available_at <= now())
                           OR (status = 'PROCESSING'
                               AND locked_until IS NOT NULL
                               AND locked_until <= now())
                        ORDER BY available_at, id
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE worker_jobs w
                    SET status = 'PROCESSING',
                        attempts = w.attempts + 1,
                        locked_until = now() + (:lease_seconds * interval '1 second'),
                        locked_by = :locked_by
                    FROM candidate c
                    WHERE w.id = c.id
                    RETURNING w.id::text, w.kind, w.payload_json, w.status,
                              w.attempts, w.locked_until, w.locked_by, w.last_error
                    """
                ),
                {"lease_seconds": self.lease_seconds, "locked_by": token},
            ).mappings().first()
        return dict(row) if row else None

    def complete_worker_job(self, job_id: str, locked_by: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE worker_jobs
                    SET status = 'DONE', locked_until = NULL,
                        locked_by = NULL, last_error = NULL
                    WHERE id = CAST(:id AS uuid)
                      AND status = 'PROCESSING'
                      AND locked_by = :locked_by
                    """
                ),
                {"id": job_id, "locked_by": locked_by},
            )
        return result.rowcount == 1

    def fail_worker_job(
        self,
        job_id: str,
        locked_by: str,
        error: str,
        *,
        retry: bool = True,
    ) -> bool:
        safe_error = error[:4000]
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE worker_jobs
                    SET status = CASE
                            WHEN :retry AND attempts < :max_attempts THEN 'PENDING'
                            ELSE 'FAILED'
                        END,
                        available_at = CASE
                            WHEN :retry AND attempts < :max_attempts
                            THEN now() + (
                                (:backoff_base * power(
                                    2, greatest(attempts - 1, 0)
                                )) * interval '1 second'
                            )
                            ELSE available_at
                        END,
                        locked_until = NULL,
                        locked_by = NULL,
                        last_error = :error
                    WHERE id = CAST(:id AS uuid)
                      AND status = 'PROCESSING'
                      AND locked_by = :locked_by
                    """
                ),
                {
                    "id": job_id,
                    "locked_by": locked_by,
                    "error": safe_error,
                    "retry": retry,
                    "max_attempts": self.max_attempts,
                    "backoff_base": self.backoff_base_seconds,
                },
            )
        return result.rowcount == 1

    def run_outbox_once(
        self,
        worker_id: str,
        handler: Callable[[ClaimedEvent], None],
    ) -> str | None:
        claimed = self.claim_outbox(worker_id)
        if claimed is None:
            return None
        try:
            handler(claimed)
        except Exception:
            self.fail_outbox(claimed.id, claimed.locked_by, retry=True)
            return "RETRY" if claimed.attempts < self.max_attempts else "FAILED"
        if not self.complete_outbox(claimed.id, claimed.locked_by):
            raise RuntimeError("OUTBOX_COMPLETION_LOST_LEASE")
        return "DONE"
