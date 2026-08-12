import base64
import hashlib
import json
import os
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

pytestmark = pytest.mark.postgres


def test_postgres_auth_event_and_audit_flow():
    from app.main import app

    client = TestClient(app)
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    public64 = base64.b64encode(public).decode()
    fingerprint = hashlib.sha256(public).hexdigest()
    user_id = f"pg-smoke-{int(time.time())}"
    enrollment = f"{user_id}:secret"
    os.environ["SENTINEL_ENROLLMENT_TOKEN"] = enrollment

    reg = client.post("/v1/devices/register", headers={"X-Enrollment-Token": enrollment}, json={"user_id": user_id, "platform": "android", "public_key_der_b64": public64, "fingerprint_sha256": fingerprint})
    assert reg.status_code == 200
    device = reg.json()

    body = {"challenge": device["challenge"], "timestamp": int(time.time()), "request_id": "pg-smoke-1"}
    signed = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    body["signature_b64"] = base64.b64encode(key.sign(signed, ec.ECDSA(hashes.SHA256()))).decode()
    proof = client.post(f"/v1/devices/{device['device_id']}/prove", json=body)
    assert proof.status_code == 200
    session = proof.json()

    event = {"events": [{"event_id": f"pg-event-{int(time.time())}", "device_id": device["device_id"], "type": "character.snapshot", "schema_version": 1, "occurred_at": "2026-08-12T06:00:00Z", "sequence": 0, "payload": {"hp": 100}}]}
    ingested = client.post("/v1/events:batch", headers={"Authorization": "Bearer " + session["session_token"], "Idempotency-Key": "pg-smoke-batch"}, json=event)
    assert ingested.status_code == 200
    assert ingested.json()["accepted"] == 1

    refreshed = client.post("/v1/sessions/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200
    audit = client.get("/v1/audit", headers={"Authorization": "Bearer " + refreshed.json()["session_token"]})
    assert audit.status_code == 200
    assert audit.json()["events"]
