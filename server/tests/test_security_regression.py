import base64
import time

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.security import AuthorizationEngine, Decision, Policy, Principal, canonical_json
from app.main import app, store


client = TestClient(app)


def _device(user_id: str = "negative-security@example.com"):
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    public64 = base64.b64encode(public).decode()
    fingerprint = __import__("hashlib").sha256(public).hexdigest()
    challenge = "initial-challenge"
    device_id = store.register_device(user_id, "android", public64, fingerprint, challenge)
    return key, device_id, challenge


def _prove(key, challenge: str, request_id: str):
    timestamp = int(time.time())
    payload = canonical_json({"challenge": challenge, "timestamp": timestamp, "request_id": request_id})
    signature = base64.b64encode(key.sign(payload, ec.ECDSA(hashes.SHA256()))).decode()
    return {"challenge": challenge, "timestamp": timestamp, "request_id": request_id, "signature_b64": signature}


def test_invalid_nonce_is_rejected():
    _, device_id, _ = _device()
    response = client.post(
        f"/v1/devices/{device_id}/prove",
        json={"challenge": "not-the-issued-challenge", "timestamp": int(time.time()), "request_id": "invalid-nonce", "signature_b64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_OR_REPLAYED_CHALLENGE"


def test_challenge_replay_is_rejected_after_first_use():
    key, device_id, _ = _device("replay@example.com")
    challenge = store.create_challenge(device_id)
    first = client.post(f"/v1/devices/{device_id}/prove", json=_prove(key, challenge, "replay-first"))
    assert first.status_code == 200
    second = client.post(f"/v1/devices/{device_id}/prove", json=_prove(key, challenge, "replay-second"))
    assert second.status_code == 401
    assert second.json()["code"] == "INVALID_OR_REPLAYED_CHALLENGE"


def test_proof_request_replay_is_rejected():
    key, device_id, _ = _device("proof-replay@example.com")
    challenge = store.create_challenge(device_id)
    payload = _prove(key, challenge, "same-request")
    first = client.post(f"/v1/devices/{device_id}/prove", json=payload)
    assert first.status_code == 200
    second_challenge = store.create_challenge(device_id)
    second_payload = _prove(key, second_challenge, "same-request")
    second = client.post(f"/v1/devices/{device_id}/prove", json=second_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "REPLAY_DETECTED"


def test_bad_signature_is_rejected():
    key, device_id, _ = _device("bad-signature@example.com")
    challenge = store.create_challenge(device_id)
    payload = _prove(key, challenge, "bad-signature")
    payload["signature_b64"] = base64.b64encode(b"not-a-signature").decode()
    response = client.post(f"/v1/devices/{device_id}/prove", json=payload)
    assert response.status_code == 401
    assert response.json()["code"] == "BAD_SIGNATURE"


def test_null_device_principal_cannot_bypass_device_scoped_event_policy():
    response = client.post(
        "/v1/auth/register",
        json={"email": "principal-bypass@example.com", "password": "Correct-Horse-Battery-Staple-123"},
    )
    token = response.json()["session_token"]
    denied = client.post(
        "/v1/authorize",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "event:write", "resource": "game:event"},
    )
    assert denied.status_code == 200
    assert denied.json()["decision"] == "DENY"


def test_wrong_role_cannot_satisfy_role_policy():
    engine = AuthorizationEngine([Policy(Decision.ALLOW, "admin:read", "admin", roles=frozenset({"admin"}))])
    assert engine.authorize(Principal("u1", None, frozenset({"user"}), frozenset()), "admin:read", "admin") == (Decision.DENY, "REQUIREMENTS_NOT_MET")


def test_explicit_deny_wins_over_allow_for_null_device_principal():
    engine = AuthorizationEngine([
        Policy(Decision.ALLOW, "game:read", "game:*", scopes=frozenset({"game:read"})),
        Policy(Decision.DENY, "game:read", "game:blocked", scopes=frozenset({"game:read"})),
    ])
    principal = Principal("u1", None, frozenset({"user"}), frozenset({"game:read"}))
    assert engine.authorize(principal, "game:read", "game:blocked") == (Decision.DENY, "POLICY_DENY")
