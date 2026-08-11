from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class Principal:
    user_id: str
    device_id: str | None
    roles: frozenset[str]
    scopes: frozenset[str]


@dataclass(frozen=True)
class Policy:
    effect: Decision
    action: str
    resource: str
    roles: frozenset[str] = frozenset()
    scopes: frozenset[str] = frozenset()

    def matches(self, action: str, resource: str) -> bool:
        action_match = self.action == "*" or self.action == action or (
            self.action.endswith(":*") and action.startswith(self.action[:-1])
        )
        resource_match = self.resource == "*" or self.resource == resource or (
            self.resource.endswith(":*") and resource.startswith(self.resource[:-1])
        )
        return action_match and resource_match


class AuthorizationEngine:
    """Default-deny RBAC + scope + policy evaluator.

    Deny rules win. A policy requiring roles/scopes only matches when the
    principal contains every required value.
    """

    def __init__(self, policies: list[Policy] | None = None) -> None:
        self._policies = policies or []

    def authorize(self, principal: Principal, action: str, resource: str) -> tuple[Decision, str]:
        matching = [p for p in self._policies if p.matches(action, resource)]
        if not matching:
            return Decision.DENY, "NO_MATCHING_POLICY"
        for policy in matching:
            if not policy.roles.issubset(principal.roles):
                continue
            if not policy.scopes.issubset(principal.scopes):
                continue
            if policy.effect is Decision.DENY:
                return Decision.DENY, "POLICY_DENY"
        for policy in matching:
            if policy.effect is Decision.ALLOW and policy.roles.issubset(principal.roles) and policy.scopes.issubset(principal.scopes):
                return Decision.ALLOW, "POLICY_ALLOW"
        return Decision.DENY, "REQUIREMENTS_NOT_MET"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def new_nonce() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def verify_p256_signature(public_key_der_b64: str, signature_b64: str, payload: bytes) -> bool:
    try:
        public_key = serialization.load_der_public_key(base64.b64decode(public_key_der_b64))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        if public_key.curve.name not in {"secp256r1", "prime256v1"}:
            return False
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False


def fingerprint_public_key(public_key_der_b64: str) -> str:
    return sha256_hex(base64.b64decode(public_key_der_b64))


def session_hash(token: str) -> str:
    return sha256_hex(token.encode("utf-8"))


def fresh_request_timestamp(timestamp: int, now: int | None = None, max_skew_seconds: int = 120) -> bool:
    current = int(time.time()) if now is None else now
    return abs(current - timestamp) <= max_skew_seconds


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())
