from __future__ import annotations

from typing import Any

from sqlalchemy import text

_BATCH = 200


class PostgresOperationalMaintenance:
    """Bounded retention cleanup for operational tables.

    Each statement deletes/updates at most one small batch to avoid long locks.
    Repeated invocations converge without requiring a paid scheduler.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def run_batch(self) -> dict[str, int]:
        statements = {
            "security_failures": "DELETE FROM security_failures WHERE ctid IN (SELECT ctid FROM security_failures WHERE failed_at < now()-interval '1 day' LIMIT :limit)",
            "idempotency_keys": "DELETE FROM idempotency_keys WHERE ctid IN (SELECT ctid FROM idempotency_keys WHERE expires_at <= now() LIMIT :limit)",
            "device_challenges": "DELETE FROM device_challenges WHERE ctid IN (SELECT ctid FROM device_challenges WHERE expires_at <= now() OR (consumed_at IS NOT NULL AND consumed_at < now()-interval '1 day') LIMIT :limit)",
            "proof_request_ids": "DELETE FROM proof_request_ids WHERE ctid IN (SELECT ctid FROM proof_request_ids WHERE created_at < now()-interval '1 day' LIMIT :limit)",
            "outbox_events": "DELETE FROM outbox_events WHERE ctid IN (SELECT ctid FROM outbox_events WHERE status IN ('DONE','FAILED') AND available_at < now()-interval '30 days' LIMIT :limit)",
            "worker_jobs": "DELETE FROM worker_jobs WHERE ctid IN (SELECT ctid FROM worker_jobs WHERE status IN ('DONE','FAILED') AND available_at < now()-interval '30 days' LIMIT :limit)",
            "companion_telemetry_events": "DELETE FROM companion_telemetry_events WHERE ctid IN (SELECT ctid FROM companion_telemetry_events WHERE expires_at <= now() LIMIT :limit)",
        }
        counts: dict[str, int] = {}
        with self.engine.begin() as conn:
            for name, sql in statements.items():
                result = conn.execute(text(sql), {"limit": _BATCH})
                counts[name] = int(result.rowcount or 0)
            stale = conn.execute(text(
                "WITH expired AS (SELECT id FROM quality_reports WHERE diagnostics_expires_at IS NOT NULL AND diagnostics_expires_at <= now() LIMIT :limit) "
                "UPDATE quality_reports q SET diagnostics_consent=false,diagnostics_json=NULL,diagnostics_bytes=0,diagnostics_expires_at=NULL,updated_at=now() "
                "FROM expired e WHERE q.id=e.id"
            ), {"limit": _BATCH})
            counts["quality_diagnostics"] = int(stale.rowcount or 0)
        return counts
