from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from app.core.operational_maintenance import PostgresOperationalMaintenance

pytestmark = pytest.mark.postgres


def test_bounded_operational_cleanup_removes_expired_rows() -> None:
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True, connect_args={"options": "-c app.service_role=true"})
    expired_key = f"expired-{uuid.uuid4().hex}"
    subject = f"failure-{uuid.uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO idempotency_keys(key,actor_id,request_hash,response_json,expires_at) VALUES (:key,:actor,'hash','{}'::jsonb,now()-interval '1 hour')"), {"key": expired_key, "actor": f"actor-{uuid.uuid4().hex}"})
        conn.execute(text("INSERT INTO security_failures(subject,source,failed_at) VALUES (:subject,'test',now()-interval '2 days')"), {"subject": subject})

    counts = PostgresOperationalMaintenance(engine).run_batch()
    assert counts["idempotency_keys"] >= 1
    assert counts["security_failures"] >= 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM idempotency_keys WHERE key=:key"), {"key": expired_key}).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM security_failures WHERE subject=:subject"), {"subject": subject}).scalar_one() == 0
    engine.dispose()
