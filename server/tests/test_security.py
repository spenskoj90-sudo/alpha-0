import base64
import hashlib
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.security import AuthorizationEngine, Decision, Policy, Principal, ScopeEngine, canonical_json, fingerprint_public_key, fresh_request_timestamp, verify_p256_signature


def principal(*, roles=(), scopes=()):
    return Principal("u1", "d1", frozenset(roles), frozenset(scopes))


def test_default_deny():
    engine = AuthorizationEngine([Policy(Decision.DENY, "*", "*")])
    assert engine.authorize(principal(), "character:read", "character:1") == (Decision.DENY, "POLICY_DENY")


def test_scope_allows():
    engine = AuthorizationEngine([Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"}))])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:1")[0] is Decision.ALLOW
    assert engine.authorize(principal(), "character:read", "character:1")[0] is Decision.DENY


def test_deny_wins():
    engine = AuthorizationEngine([Policy(Decision.ALLOW, "character:read", "character:*", scopes=frozenset({"character:read"})), Policy(Decision.DENY, "character:read", "character:secret", scopes=frozenset({"character:read"}))])
    assert engine.authorize(principal(scopes=("character:read",)), "character:read", "character:secret")[0] is Decision.DENY


def test_scope_composition_is_least_privilege():
    assert ScopeEngine.compose(["game:read", "game:write"], ["game:read"]) == frozenset({"game:read"})
    with pytest.raises(ValueError, match="SCOPE_NOT_GRANTED"):
        ScopeEngine.compose(["game:read"], ["game:write"])


def test_canonical_json_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_p256_signature_and_fingerprint():
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    public64 = base64.b64encode(public).decode()
    payload = canonical_json({"challenge": "abc", "timestamp": int(time.time()), "request_id": "r1"})
    signature = base64.b64encode(key.sign(payload, ec.ECDSA(hashes.SHA256()))).decode()
    assert verify_p256_signature(public64, signature, payload)
    assert not verify_p256_signature(public64, signature, payload + b"x")
    assert fingerprint_public_key(public64) == hashlib.sha256(public).hexdigest()


def test_timestamp_window():
    assert fresh_request_timestamp(1000, now=1000)
    assert fresh_request_timestamp(1000, now=1100, max_skew_seconds=120)
    assert not fresh_request_timestamp(1000, now=1201, max_skew_seconds=120)
