import base64
import hashlib
import json
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.postgres


def _key_material():
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return key, base64.b64encode(public).decode(), hashlib.sha256(public).hexdigest()


def test_postgres_auth_event_and_audit_flow():
    from app.main import REFRESH_TTL_SECONDS, SESSION_TTL_SECONDS, app, store
    from app.core.store import PostgresStore

    assert isinstance(store, PostgresStore)
    client = TestClient(app)
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "UP"

    key, public64, fingerprint = _key_material()
    user_id = "pg-smoke"
    enrollment = "pg-smoke:secret"

    reg = client.post(
        "/v1/devices/register",
        headers={"X-Enrollment-Token": enrollment},
        json={
            "user_id": user_id,
            "platform": "android",
            "public_key_der_b64": public64,
            "fingerprint_sha256": fingerprint,
        },
    )
    assert reg.status_code == 200
    device = reg.json()
    device_id = device["device_id"]

    body = {
        "challenge": device["challenge"],
        "timestamp": int(time.time()),
        "request_id": "pg-smoke-1",
    }
    signed = json.dumps(
        {"challenge": body["challenge"], "timestamp": body["timestamp"], "request_id": body["request_id"]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    body["signature_b64"] = base64.b64encode(key.sign(signed, ec.ECDSA(hashes.SHA256()))).decode()
    proof = client.post(f"/v1/devices/{device_id}/prove", json=body)
    assert proof.status_code == 200
    session = proof.json()

    event = {
        "events": [
            {
                "event_id": "pg-event-1",
                "device_id": device_id,
                "type": "character.snapshot",
                "schema_version": 1,
                "occurred_at": "2026-08-12T06:00:00Z",
                "sequence": 0,
                "payload": {"hp": 100},
            }
        ]
    }
    ingested = client.post(
        "/v1/events:batch",
        headers={"Authorization": "Bearer " + session["session_token"], "Idempotency-Key": "pg-smoke-batch"},
        json=event,
    )
    assert ingested.status_code == 200
    assert ingested.json()["accepted"] == 1

    refreshed = client.post("/v1/sessions/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200
    audit = client.get(
        "/v1/audit",
        headers={"Authorization": "Bearer " + refreshed.json()["session_token"]},
    )
    assert audit.status_code == 200
    assert audit.json()["events"]

    with store.engine.connect() as conn:
        device_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": device_id},
        ).scalar_one()
        active_sessions = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) AND revoked_at IS NULL"
            ),
            {"id": device_id},
        ).scalar_one()
        prove_allow = conn.execute(
            text(
                "SELECT COUNT(*) FROM audit_events "
                "WHERE action = 'device:prove' AND decision = 'ALLOW' "
                "AND device_id = CAST(:id AS uuid)"
            ),
            {"id": device_id},
        ).scalar_one()
        event_count = conn.execute(
            text("SELECT COUNT(*) FROM game_events WHERE event_id = :eid"),
            {"eid": "pg-event-1"},
        ).scalar_one()
        migration_versions = {
            row[0]
            for row in conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
        }

    assert device_state == "ACTIVE"
    assert active_sessions >= 1
    assert prove_allow >= 1
    assert event_count == 1
    assert {"001_initial", "002_p1_rls", "003_user_auth"}.issubset(migration_versions)

    # Recycle the SQLAlchemy connection pool and prove the application still reads durable state.
    store.engine.dispose()
    health_after_recycle = client.get("/healthz")
    assert health_after_recycle.status_code == 200
    audit_after_recycle = client.get(
        "/v1/audit",
        headers={"Authorization": "Bearer " + refreshed.json()["session_token"]},
    )
    assert audit_after_recycle.status_code == 200
    assert audit_after_recycle.json()["events"]

    # Minimal Postgres bind happy-path: session without device, then bind a new key.
    bind_key, bind_public64, bind_fingerprint = _key_material()
    bind_access, _, _, _ = store.issue_session(None, user_id, SESSION_TTL_SECONDS, REFRESH_TTL_SECONDS)
    bound = client.post(
        "/v1/devices/bind",
        headers={"Authorization": "Bearer " + bind_access},
        json={
            "platform": "android",
            "public_key_der_b64": bind_public64,
            "fingerprint_sha256": bind_fingerprint,
        },
    )
    assert bound.status_code == 200, bound.text
    bound_device_id = bound.json()["device_id"]
    assert bound_device_id != device_id

    with store.engine.connect() as conn:
        bind_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": bound_device_id},
        ).scalar_one()
        linked = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
    assert bind_state == "ACTIVE"
    assert linked >= 1

    # Optional revoke continuation of the bound device.
    revoked = client.post(
        f"/v1/devices/{bound_device_id}/revoke",
        headers={"Authorization": "Bearer " + bind_access},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json() == {"revoked": True}

    with store.engine.connect() as conn:
        revoked_state = conn.execute(
            text("SELECT state FROM device_bindings WHERE id = CAST(:id AS uuid)"),
            {"id": bound_device_id},
        ).scalar_one()
        revoked_sessions = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NOT NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
        still_active = conn.execute(
            text(
                "SELECT COUNT(*) FROM sessions WHERE device_id = CAST(:id AS uuid) "
                "AND revoked_at IS NULL"
            ),
            {"id": bound_device_id},
        ).scalar_one()
    assert revoked_state == "REVOKED"
    assert revoked_sessions >= 1
    assert still_active == 0
