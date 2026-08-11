from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
from typing import FrozenSet


@dataclass(frozen=True)
class AuthzContext:
    actor_id: str | None
    device_id: str | None
    roles: FrozenSet[str]
    scopes: FrozenSet[str]
    entitlements: FrozenSet[str]


@dataclass(frozen=True)
class Policy:
    action: str
    required_roles: FrozenSet[str] = frozenset()
    required_scopes: FrozenSet[str] = frozenset()
    required_entitlements: FrozenSet[str] = frozenset()


class AuthorizationEngine:
    """Pure, deterministic authorization decision engine with default deny."""

    def __init__(self, policies: tuple[Policy, ...]) -> None:
        self._policies = {p.action: p for p in policies}

    def authorize(self, ctx: AuthzContext, action: str) -> bool:
        if not ctx.actor_id:
            return False
        policy = self._policies.get(action)
        if policy is None:
            return False
        return (
            policy.required_roles.issubset(ctx.roles)
            and policy.required_scopes.issubset(ctx.scopes)
            and policy.required_entitlements.issubset(ctx.entitlements)
        )


class ReplayGuard:
    """Nonce verifier with one-time consumption and bounded clock skew."""

    def __init__(self, max_skew_seconds: int = 30) -> None:
        self.max_skew_seconds = max_skew_seconds
        self._consumed: set[str] = set()

    def is_valid(self, nonce: str, expires_at: datetime, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return nonce not in self._consumed and expires_at.timestamp() + self.max_skew_seconds >= now.timestamp()

    def consume(self, nonce: str) -> None:
        self._consumed.add(nonce)

    def verify_and_consume(self, nonce: str, expires_at: datetime, now: datetime | None = None) -> bool:
        if not self.is_valid(nonce, expires_at, now):
            return False
        self.consume(nonce)
        return True


def canonical_session_message(session_id: str, device_id: str, nonce: str, request_hash: bytes) -> bytes:
    domain = b"SENTINEL_SESSION_V1"
    return b"|".join((domain, session_id.encode(), device_id.encode(), nonce.encode(), request_hash.hex().encode()))


def request_digest(body: bytes) -> bytes:
    return sha256(body).digest()


def constant_time_equal(left: bytes, right: bytes) -> bool:
    return hmac.compare_digest(left, right)
