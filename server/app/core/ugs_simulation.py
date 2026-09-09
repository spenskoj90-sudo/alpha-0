from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Iterable

from app.core.unified_game_state import UGSIngestor, UGSState


@dataclass(frozen=True, slots=True)
class UGSSimulationStep:
    """One deterministic input and the observable ingest result."""

    state: UGSState
    now: datetime


@dataclass(frozen=True, slots=True)
class UGSSimulationObservation:
    """Stable, JSON-serializable outcome for one simulation step."""

    session_id: str
    sequence: int
    accepted: bool
    fresh: bool
    expired: bool
    usable_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UGSSimulationResult:
    """Complete deterministic simulation result with a reproducible digest."""

    observations: tuple[UGSSimulationObservation, ...]

    def canonical_bytes(self) -> bytes:
        payload = [
            {
                "session_id": item.session_id,
                "sequence": item.sequence,
                "accepted": item.accepted,
                "fresh": item.fresh,
                "expired": item.expired,
                "usable_capabilities": list(item.usable_capabilities),
            }
            for item in self.observations
        ]
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def digest(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()


class DeterministicUGSSimulation:
    """Replay UGS inputs through the runtime validator without wall-clock state.

    The harness deliberately models only Core validation semantics. It performs no
    actions, network I/O, provider calls, or game-process interaction. Callers own
    the supplied timestamps, making the result reproducible across environments.
    """

    def __init__(self, *, freshness_seconds: float = 10.0) -> None:
        self._ingestor = UGSIngestor(freshness_seconds=freshness_seconds)

    def run(self, steps: Iterable[UGSSimulationStep]) -> UGSSimulationResult:
        observations: list[UGSSimulationObservation] = []
        for step in steps:
            state = step.state
            fresh = self._ingestor.is_fresh(state, now=step.now)
            accepted = self._ingestor.accept(state)
            expired_state = self._ingestor.expire(
                session_id=state.session_id,
                now=step.now,
            )
            effective_state = expired_state or state
            usable_capabilities = tuple(
                sorted(
                    name
                    for name in effective_state.capabilities
                    if fresh and self._ingestor.usable_capability(effective_state, name)
                )
            )
            observations.append(
                UGSSimulationObservation(
                    session_id=state.session_id,
                    sequence=state.sequence,
                    accepted=accepted,
                    fresh=fresh,
                    expired=(
                        expired_state is not None
                        and "stale_state" in expired_state.missing_signals
                    ),
                    usable_capabilities=usable_capabilities,
                )
            )
        return UGSSimulationResult(observations=tuple(observations))
