from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text

from app.core.event_runtime import PostgresEventRuntime


@pytest.mark.postgres
def test_outbox_lease_retry_dlq_and_replay():
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, connect_args={"options": "-c app.service_role=true"})
    event_id = str(uuid.uuid4())
    with engine.begin() as conn:
        identity = conn.execute(text("INSERT INTO identities(user_handle) VALUES (:u) RETURNING id"), {"u": f"runtime-{event_id}"}).scalar_one()
        device = conn.execute(text("INSERT INTO device_bindings(identity_id,fingerprint_sha256,public_key_der_b64,platform) VALUES (:i,:fp,:key,'android') RETURNING id"), {"i": identity, "fp": event_id.replace('-', '')[:64], "key": "runtime"}).scalar_one()
        outbox = conn.execute(text("INSERT INTO outbox_events(aggregate_type,aggregate_id,event_type,payload_json) VALUES ('game_event',:a,'runtime.test','{}'::jsonb) RETURNING id::text"), {"a": device}).scalar_one()

    runtime = PostgresEventRuntime(database_url, lease_seconds=30, max_attempts=2, backoff_base_seconds=1)
    first = runtime.claim_outbox("worker-a")
    assert first is not None and first.id == outbox and first.attempts == 1
    assert runtime.complete_outbox(first.id, "wrong-token") is False
    assert runtime.fail_outbox(first.id, first.locked_by, retry=True) is True

    with engine.begin() as conn:
        conn.execute(text("UPDATE outbox_events SET available_at=now() WHERE id=CAST(:id AS uuid)"), {"id": outbox})
    second = runtime.claim_outbox("worker-a")
    assert second is not None and second.attempts == 2
    assert runtime.fail_outbox(second.id, second.locked_by, retry=True) is True

    with engine.connect() as conn:
        status = conn.execute(text("SELECT status FROM outbox_events WHERE id=CAST(:id AS uuid)"), {"id": outbox}).scalar_one()
    assert status == "FAILED"
    assert runtime.replay_failed_outbox(outbox) is True

    with engine.connect() as conn:
        status, attempts = conn.execute(text("SELECT status, attempts FROM outbox_events WHERE id=CAST(:id AS uuid)"), {"id": outbox}).one()
    assert status == "PENDING" and attempts == 0


@pytest.mark.postgres
def test_worker_job_lease_owner_and_error_are_durable():
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, connect_args={"options": "-c app.service_role=true"})
    with engine.begin() as conn:
        job_id = conn.execute(text("INSERT INTO worker_jobs(kind,payload_json) VALUES ('runtime.test','{}'::jsonb) RETURNING id::text")).scalar_one()

    runtime = PostgresEventRuntime(database_url, lease_seconds=30, max_attempts=3, backoff_base_seconds=1)
    job = runtime.claim_worker_job("worker-a")
    assert job is not None and job["id"] == job_id and job["attempts"] == 1
    assert runtime.complete_worker_job(job_id, "wrong-token") is False
    assert runtime.fail_worker_job(job_id, job["locked_by"], "transient failure", retry=False) is True

    with engine.connect() as conn:
        status, error = conn.execute(text("SELECT status,last_error FROM worker_jobs WHERE id=CAST(:id AS uuid)"), {"id": job_id}).one()
    assert status == "FAILED" and error == "transient failure"
