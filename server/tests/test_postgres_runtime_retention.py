from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text

from app.core.retention import purge_expired_runtime_data

pytestmark = pytest.mark.postgres


def test_runtime_retention_deletes_expired_rows_and_preserves_recent_rows():
    marker = uuid.uuid4().hex
    old_outbox = str(uuid.uuid4())
    fresh_outbox = str(uuid.uuid4())
    old_worker = str(uuid.uuid4())
    fresh_worker = str(uuid.uuid4())
    engine = create_engine(
        os.environ["DATABASE_URL"],
        pool_pre_ping=True,
        connect_args={"options": "-c app.service_role=true"},
    )
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO idempotency_keys(key,actor_id,request_hash,response_json,created_at,expires_at) "
                    "VALUES (:old,:actor,'old','{}'::jsonb,now()-interval '2 days',now()-interval '1 day'),"
                    "(:fresh,:actor,'fresh','{}'::jsonb,now(),now()+interval '1 day')"
                ),
                {"old": f"old-{marker}", "fresh": f"fresh-{marker}", "actor": f"actor-{marker}"},
            )
            conn.execute(
                text(
                    "INSERT INTO security_failures(subject,source,failed_at) VALUES "
                    "(:old,'retention-test',now()-interval '2 days'),"
                    "(:fresh,'retention-test',now())"
                ),
                {"old": f"old-{marker}", "fresh": f"fresh-{marker}"},
            )
            conn.execute(
                text(
                    "INSERT INTO outbox_events(id,aggregate_type,event_type,payload_json,status,available_at) VALUES "
                    "(CAST(:old AS uuid),'retention-test','test','{}'::jsonb,'DONE',now()-interval '8 days'),"
                    "(CAST(:fresh AS uuid),'retention-test','test','{}'::jsonb,'DONE',now())"
                ),
                {"old": old_outbox, "fresh": fresh_outbox},
            )
            conn.execute(
                text(
                    "INSERT INTO worker_jobs(id,kind,payload_json,status,available_at) VALUES "
                    "(CAST(:old AS uuid),'retention-test','{}'::jsonb,'FAILED',now()-interval '8 days'),"
                    "(CAST(:fresh AS uuid),'retention-test','{}'::jsonb,'FAILED',now())"
                ),
                {"old": old_worker, "fresh": fresh_worker},
            )

        deleted = purge_expired_runtime_data(engine, batch_size=100)
        assert deleted["idempotency_keys"] >= 1
        assert deleted["security_failures"] >= 1
        assert deleted["outbox_events"] >= 1
        assert deleted["worker_jobs"] >= 1

        with engine.begin() as conn:
            assert conn.execute(text("SELECT 1 FROM idempotency_keys WHERE key=:k"), {"k": f"old-{marker}"}).first() is None
            assert conn.execute(text("SELECT 1 FROM security_failures WHERE subject=:s"), {"s": f"old-{marker}"}).first() is None
            assert conn.execute(text("SELECT 1 FROM outbox_events WHERE id=CAST(:id AS uuid)"), {"id": old_outbox}).first() is None
            assert conn.execute(text("SELECT 1 FROM worker_jobs WHERE id=CAST(:id AS uuid)"), {"id": old_worker}).first() is None

            assert conn.execute(text("SELECT 1 FROM idempotency_keys WHERE key=:k"), {"k": f"fresh-{marker}"}).first()
            assert conn.execute(text("SELECT 1 FROM security_failures WHERE subject=:s"), {"s": f"fresh-{marker}"}).first()
            assert conn.execute(text("SELECT 1 FROM outbox_events WHERE id=CAST(:id AS uuid)"), {"id": fresh_outbox}).first()
            assert conn.execute(text("SELECT 1 FROM worker_jobs WHERE id=CAST(:id AS uuid)"), {"id": fresh_worker}).first()

            conn.execute(text("DELETE FROM idempotency_keys WHERE actor_id=:actor"), {"actor": f"actor-{marker}"})
            conn.execute(text("DELETE FROM security_failures WHERE source='retention-test' AND subject LIKE :pattern"), {"pattern": f"%-{marker}"})
            conn.execute(text("DELETE FROM outbox_events WHERE aggregate_type='retention-test' AND id IN (CAST(:a AS uuid),CAST(:b AS uuid))"), {"a": old_outbox, "b": fresh_outbox})
            conn.execute(text("DELETE FROM worker_jobs WHERE kind='retention-test' AND id IN (CAST(:a AS uuid),CAST(:b AS uuid))"), {"a": old_worker, "b": fresh_worker})
    finally:
        engine.dispose()
