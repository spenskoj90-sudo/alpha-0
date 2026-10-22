"""In-memory L2-only game module lifecycle replay; no production source attestation.

Replay signals describe the presence of simulated fields, never their values.
The existing authenticated inventory remains UNKNOWN and NOT_STARTED.
Nothing in this sandbox can authorize real-world actions or promote L3 readiness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .game_source_modules import ExactSourceProfile

MAX_AGE_MS = 5_000
MAX_CLOCK_MS = 2**63 - 1


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    """A deliberately synthetic checkpoint or observation inside one replay."""

    profile_id: str
    session_id: str
    sequence: int
    observed_ms: int
    fields_present: tuple[str, ...]
    kind: Literal["checkpoint", "session"]


class ModuleLifecycleReplay:
    """Deterministic shared-signal reducer for bounded L2 tests only.

    No endpoint calls this class. Instantiating it carries no trust,
    entitlement, capture permission or action-execution capability.
    """

    def __init__(self, profile: ExactSourceProfile, *, session_id: str):
        if type(profile) is not ExactSourceProfile or not isinstance(session_id, str) or not 1 <= len(session_id) <= 128:
            raise ValueError("REPLAY_IDENTITY_INVALID")
        self.profile = profile
        self.session_id = session_id
        self._signals: dict[str, int] = {}
        self._sequence = 0
        self._last_observed = -1
        self._last_now = -1
        self._stopped = False

    @staticmethod
    def _clock(value: int) -> None:
        if type(value) is not int or not 0 <= value <= MAX_CLOCK_MS:
            raise ValueError("REPLAY_CLOCK_INVALID")

    def observe(self, frame: ReplayFrame, *, now_ms: int) -> None:
        """Validate the entire replay frame before any state mutation."""
        self._clock(now_ms)
        if self._stopped:
            raise ValueError("REPLAY_STOPPED")
        if type(frame) is not ReplayFrame or frame.session_id != self.session_id or frame.profile_id != self.profile.profile_id:
            raise ValueError("REPLAY_PROFILE_SESSION_MISMATCH")
        self._clock(frame.observed_ms)
        if now_ms < self._last_now or frame.observed_ms < self._last_observed:
            raise ValueError("REPLAY_CLOCK_ROLLBACK")
        if frame.observed_ms > now_ms or now_ms - frame.observed_ms > MAX_AGE_MS:
            raise ValueError("REPLAY_STALE_SOURCE")
        if type(frame.sequence) is not int or frame.sequence != self._sequence + 1:
            raise ValueError("REPLAY_SEQUENCE_INVALID")
        if frame.kind not in ("checkpoint", "session"):
            raise ValueError("REPLAY_SOURCE_KIND_INVALID")
        if type(frame.fields_present) is not tuple or not 1 <= len(frame.fields_present) <= 64:
            raise ValueError("REPLAY_FIELDS_INVALID")
        if any(type(name) is not str or not name or len(name) > 64 for name in frame.fields_present):
            raise ValueError("REPLAY_FIELDS_INVALID")
        if len(set(frame.fields_present)) != len(frame.fields_present):
            raise ValueError("REPLAY_FIELDS_DUPLICATE")
        declared = {field.id: field for field in self.profile.fields}
        if any(name not in declared for name in frame.fields_present):
            raise ValueError("REPLAY_FIELD_NOT_DECLARED")
        if frame.kind != "checkpoint" and any(
            declared[name].source_type == "saved_variables" for name in frame.fields_present
        ):
            raise ValueError("REPLAY_CHECKPOINT_REQUIRED")

        if frame.kind == "checkpoint":
            # A new checkpoint supersedes older snapshot presence; it is not a
            # near-real-time stream and must not silently preserve old signals.
            self._signals.clear()
        for name in frame.fields_present:
            self._signals[name] = frame.observed_ms
        self._sequence = frame.sequence
        self._last_observed = frame.observed_ms
        self._last_now = now_ms

    def snapshot(self, *, now_ms: int) -> dict:
        self._clock(now_ms)
        if now_ms < self._last_now:
            raise ValueError("REPLAY_CLOCK_ROLLBACK")
        # Aging does not extend field lifetime; a paused/restarted replay
        # cannot turn previously stale evidence fresh.
        self._last_now = now_ms
        present = {
            key for key, observed in self._signals.items()
            if not self._stopped and 0 <= now_ms - observed <= MAX_AGE_MS
        }
        status: dict[str, str] = {}
        result = []
        for module in self.profile.modules:
            missing = sorted(set(module.fields) - present)
            # The source-map's DAG is already validated at load; recursion
            # also handles declarations supplied in dependency-last order.
            def blockers(module_id: str, stack: frozenset[str] = frozenset()) -> bool:
                if module_id in stack:
                    return True
                dependency = next((m for m in self.profile.modules if m.id == module_id), None)
                if dependency is None or any(f not in present for f in dependency.fields):
                    return True
                return any(blockers(d, stack | {module_id}) for d in dependency.dependencies)

            blocked = any(blockers(dep) for dep in module.dependencies)
            if self._stopped:
                readiness = "STOPPED"
            elif missing:
                readiness = "WAITING_FOR_SOURCE"
            elif blocked:
                readiness = "BLOCKED_BY_DEPENDENCY"
            else:
                readiness = "L2_SIMULATED_ONLY"
            status[module.id] = readiness
            result.append({
                "id": module.id,
                "lifecycle_status": readiness,
                "missing_signals": missing,
                "synthetic_signals": sorted(set(module.fields) & present),
                "outputs_available": [],
                "execution_authority": False,
            })
        return {
            "evidence": "L2_SYNTHETIC_ONLY",
            "source_trust": "UNVERIFIED",
            "profile_id": self.profile.profile_id,
            "session_id": self.session_id if not self._stopped else None,
            "sequence": self._sequence,
            "shared_player_state": {
                "schema_version": 1, "availability": "UNKNOWN",
                "session_binding": None, "last_updated_ms": None,
            },
            "modules": result,
            "execution_authority": False,
        }

    def stop(self) -> None:
        self._stopped = True
        self._signals.clear()
