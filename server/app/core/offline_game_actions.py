"""Versioned action plumbing for one in-memory offline fixture only.

There is no platform executor, network route, game integration or persistent
grant here. The existing ActionGateway AUTOMATIC denial remains unchanged.
The caller owns a single thread and supplies monotonic elapsed milliseconds.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .action_gateway import ActionDecision, ActionGateway, ActionMode, ActionRequest
from .game_adapter import CapabilityStatus
from .security import Principal


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    game: str = Field(min_length=1, max_length=64)
    package: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    environment: str = Field(min_length=1, max_length=64)
    profile: str = Field(min_length=1, max_length=64)


FIXTURE_TARGET = Target(game="sentinel-turn-fixture", package="sentinel.offline.fixture", version="1",
                        environment="local-offline-replay", profile="turn-v1")


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ActionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal["sentinel.game-action.v1"]
    target: Target
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    action_id: Literal["advance_turn"]
    arguments: NoArguments
    idempotency_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    sequence: int = Field(ge=0, le=2_100_000_000)
    state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_ms: int = Field(ge=0)


@dataclass(frozen=True)
class Observation:
    sequence: int
    turn: int
    observed_ms: int
    digest: str


@dataclass(frozen=True)
class Outcome:
    outcome: Literal["SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"]
    reason: str
    observed_sequence: int | None = None


class TurnWorld:
    """Ordinary independent fixture world; it cannot deliver OS/game input."""
    target = FIXTURE_TARGET

    def __init__(self, session_id: str, *, fault: str | None = None):
        if fault not in (None, "missing_outcome", "wrong_outcome", "exception"):
            raise ValueError("FIXTURE_FAULT_INVALID")
        self.session_id = session_id
        self.turn = 0
        self.sequence = 0
        self.fault = fault

    def observe(self, now_ms: int) -> Observation:
        canonical = json.dumps({"target": self.target.model_dump(), "session": self.session_id,
                                "sequence": self.sequence, "turn": self.turn}, sort_keys=True, separators=(",", ":"))
        return Observation(self.sequence, self.turn, now_ms, sha256(canonical.encode()).hexdigest())

    def advance(self) -> None:
        self.turn += 1
        self.sequence += 1

    def deliver(self, now_ms: int) -> Observation | None:
        self.advance()
        if self.fault == "exception":
            raise RuntimeError("FIXTURE_DELIVERY_UNCERTAIN")
        if self.fault == "missing_outcome":
            return None
        if self.fault == "wrong_outcome":
            self.turn += 1
        return self.observe(now_ms)


class OfflineActionSession:
    """One pending action, at most three remembered requests and a Stop latch.

    A trusted gateway rechecks policy and entitlement before each delivery.
    Incoming requests cannot supply capability status, identity, entitlement,
    arming or execution code. No real target can enter this fixture boundary.
    """
    def __init__(self, world: TurnWorld, gateway: ActionGateway):
        if type(world) is not TurnWorld or world.target != FIXTURE_TARGET:
            raise ValueError("OFFLINE_FIXTURE_ONLY")
        self.world = world
        self.gateway = gateway
        self.pending: ActionIntent | None = None
        self.stopped = True
        self._history: dict[str, tuple[str, Outcome]] = {}
        self._principal: Principal | None = None
        self._last_now = -1
        self._last_delivery = -1000
        self._steps = 0

    def arm(self, principal: Principal, *, now_ms: int, expires_ms: int, mode: str, steps: int, confirmed: bool) -> None:
        # Rearming does not erase idempotency history, resurrect a queued action,
        # or reuse an uncertain session. A fresh session is required after Stop.
        if self._principal is not None:
            raise ValueError("SESSION_ALREADY_ARMED")
        if not principal.user_id or not principal.device_id:
            raise ValueError("PRINCIPAL_REQUIRED")
        if confirmed is not True or mode not in ("USER_CONFIRMED", "BOUNDED_RULE"):
            raise ValueError("CONSENT_REQUIRED")
        if type(now_ms) is not int or type(expires_ms) is not int or not 0 <= now_ms < expires_ms <= now_ms + 30000:
            raise ValueError("LEASE_INVALID")
        if type(steps) is not int or not 1 <= steps <= (1 if mode == "USER_CONFIRMED" else 3):
            raise ValueError("BUDGET_INVALID")
        self._principal = principal
        self._session_id = self.world.session_id
        self._expires = expires_ms
        self._mode = mode
        self._budget = steps
        self._last_now = now_ms
        self.stopped = False

    def stop(self, reason: str = "explicit") -> None:
        if self.pending is not None:
            request = self.pending
            self._history[request.idempotency_key] = (self._fingerprint(request), Outcome("CANCELLED", "STOPPED"))
        self.pending = None
        self.stopped = True

    @staticmethod
    def _fingerprint(request: ActionIntent) -> str:
        return sha256(request.model_dump_json().encode()).hexdigest()

    def _validate(self, principal: Principal, request: ActionIntent, now_ms: int, *, scheduled_ms: int) -> Observation:
        if type(now_ms) is not int or now_ms < self._last_now:
            raise ValueError("CLOCK_ROLLBACK")
        self._last_now = now_ms
        if self.stopped:
            raise ValueError("STOPPED")
        if principal != self._principal:
            raise ValueError("PRINCIPAL_MISMATCH")
        if self.world.target != FIXTURE_TARGET or request.target != FIXTURE_TARGET or request.session_id != self._session_id or self.world.session_id != self._session_id:
            raise ValueError("TARGET_MISMATCH")
        if now_ms >= self._expires or not now_ms < request.expires_ms <= scheduled_ms + 3000:
            raise ValueError("EXPIRED")
        if now_ms - scheduled_ms > 1500:
            raise ValueError("STALE_STATE")
        state = self.world.observe(now_ms)
        if request.sequence != state.sequence or request.state_digest != state.digest:
            raise ValueError("STATE_MISMATCH")
        if self._steps >= self._budget or (self._mode == "BOUNDED_RULE" and state.turn >= 3):
            raise ValueError("BUDGET_EXHAUSTED")
        if now_ms - self._last_delivery < 1000:
            raise ValueError("RATE_LIMIT")
        decision = self.gateway.authorize(principal, ActionRequest(action="offline:advance", resource="offline:turn-world",
            mode=ActionMode.USER_CONFIRMED, capability="offline_fixture", capability_status=CapabilityStatus.LIMITED, evidence_level="L2"),
            required_capabilities=("offline_fixture",), required_entitlements=("offline-game-test",))
        if decision.decision is not ActionDecision.ALLOW:
            raise ValueError(decision.reason_code)
        return state

    def schedule(self, principal: Principal, request: ActionIntent, *, now_ms: int) -> Outcome | None:
        known = self._history.get(request.idempotency_key)
        if known is not None:
            if known[0] != self._fingerprint(request):
                raise ValueError("IDEMPOTENCY_CONFLICT")
            # No state/history disclosure across principals, even for a duplicate.
            if principal != self._principal:
                raise ValueError("PRINCIPAL_MISMATCH")
            return known[1]
        if self.pending is not None:
            if self.pending == request and principal == self._principal:
                return None
            raise ValueError("QUEUE_FULL")
        self._validate(principal, request, now_ms, scheduled_ms=now_ms)
        self.pending = request
        self._scheduled_ms = now_ms
        return None

    def drain(self, principal: Principal, *, now_ms: int) -> Outcome | None:
        request = self.pending
        if request is None:
            return None
        self.pending = None
        try:
            before = self._validate(principal, request, now_ms, scheduled_ms=self._scheduled_ms)
        except ValueError as error:
            result = Outcome("CANCELLED", str(error))
            self.stop()
        else:
            # Reserve step/rate before delivery; exceptions and lost outcomes
            # consume the budget because a side effect may already have happened.
            self._steps += 1
            self._last_delivery = now_ms
            try:
                after = self.world.deliver(now_ms)
                expected = self.world.observe(now_ms)
                success = after is not None and after == expected and after.sequence == before.sequence + 1 and after.turn == before.turn + 1
            except Exception:
                after, success = None, False
            result = Outcome("SUCCEEDED", "NEW_OBSERVED_OUTCOME", after.sequence) if success else Outcome("UNKNOWN", "OUTCOME_UNVERIFIED")
            if not success:
                self.stop()
        self._history[request.idempotency_key] = (self._fingerprint(request), result)
        return result
