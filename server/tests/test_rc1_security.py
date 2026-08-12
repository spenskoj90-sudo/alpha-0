import base64
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core.security import (
    AuthorizationEngine,
    Decision,
    Policy,
    Principal,
    canonical_json,
    fingerprint_public_key,
    fresh_request_timestamp,
    verify_p256_signature,
)
from app.main import app


def test_missing_policy_is_default_deny():
    engine = AuthorizationEngine([])
    result = engine.authorize(Principal("u", None, frozenset(), frozenset()), "admin:delete", "system")
    assert result == (Decision.DENY, "NO_MATCHING_POLICY")


def test_role_without_scope_cannot_authorize():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "character:read", "character:*", roles=frozenset({"user"}), scopes=frozenset({"character:read"}))
    ])
    principal = Principal("u", "d", frozenset({"user"}), frozenset())
    assert engine.authorize(principal, "character:read", "character:1")[0] is Decision.DENY


def test_p256_signature_and_tamper_detection():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    encoded = base64.b64encode(der).decode()
    payload = canonical_json({"challenge": "c", "timestamp": 1000, "request_id": "r"})
    signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
    signature_b64 = base64.b64encode(signature).decode()

    assert verify_p256_signature(encoded, signature_b64, payload)
    assert not verify_p256_signature(encoded, signature_b64, payload + b"tamper")
    assert fingerprint_public_key(encoded)


def test_replay_window_is_bounded():
    now = int(time.time())
    assert fresh_request_timestamp(now, now=now)
    assert not fresh_request_timestamp(now - 121, now=now)
    assert not fresh_request_timestamp(now + 121, now=now)


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "sentinel-core"
