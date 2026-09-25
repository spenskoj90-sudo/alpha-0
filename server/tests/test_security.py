import base64
import hashlib
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

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



def test_policy_matching_covers_exact_global_and_prefix_wildcards():
    assert Policy(Decision.ALLOW, "*", "*").matches("any:action", "any:resource")
    assert Policy(Decision.ALLOW, "game:*", "character:*").matches("game:read", "character:1")
    assert not Policy(Decision.ALLOW, "game:*", "character:*").matches("billing:read", "character:1")
    assert not Policy(Decision.ALLOW, "game:*", "character:*").matches("game:read", "device:1")


def test_authorization_engine_distinguishes_no_policy_roles_scopes_and_allow_paths():
    engine = AuthorizationEngine(
        [
            Policy(
                Decision.ALLOW,
                "game:read",
                "game:*",
                roles=frozenset({"member"}),
                scopes=frozenset({"game:read"}),
            ),
            Policy(
                Decision.DENY,
                "game:read",
                "game:restricted",
                roles=frozenset({"admin"}),
            ),
        ]
    )
    assert engine.authorize(principal(), "billing:read", "billing:plans") == (
        Decision.DENY,
        "NO_MATCHING_POLICY",
    )
    assert engine.authorize(
        principal(scopes=("game:read",)), "game:read", "game:wow"
    ) == (Decision.DENY, "REQUIREMENTS_NOT_MET")
    assert engine.authorize(
        principal(roles=("member",)), "game:read", "game:wow"
    ) == (Decision.DENY, "REQUIREMENTS_NOT_MET")
    assert engine.authorize(
        principal(roles=("member",), scopes=("game:read",)),
        "game:read",
        "game:wow",
    ) == (Decision.ALLOW, "POLICY_ALLOW")
    # A DENY policy whose role requirement is not satisfied does not override
    # an otherwise valid ALLOW.
    assert engine.authorize(
        principal(roles=("member",), scopes=("game:read",)),
        "game:read",
        "game:restricted",
    ) == (Decision.ALLOW, "POLICY_ALLOW")


def test_signature_verifier_rejects_non_ec_wrong_curve_and_malformed_material():
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_public = rsa_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    assert verify_p256_signature(
        base64.b64encode(rsa_public).decode(),
        base64.b64encode(b"signature").decode(),
        b"payload",
    ) is False

    p384 = ec.generate_private_key(ec.SECP384R1())
    p384_public = p384.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    p384_sig = p384.sign(b"payload", ec.ECDSA(hashes.SHA256()))
    assert verify_p256_signature(
        base64.b64encode(p384_public).decode(),
        base64.b64encode(p384_sig).decode(),
        b"payload",
    ) is False

    assert verify_p256_signature("not-base64", "not-base64", b"payload") is False


def test_timestamp_default_clock_and_constant_time_helper(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    assert fresh_request_timestamp(1000) is True
    from app.core.security import constant_time_equal
    assert constant_time_equal("same", "same") is True
    assert constant_time_equal("left", "right") is False
