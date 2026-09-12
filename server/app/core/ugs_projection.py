from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.core.unified_game_state import UGSState

Projection = Callable[[UGSState], Any]


@dataclass(frozen=True)
class ProjectionResult:
    sequence: int
    applied: tuple[str, ...]


class UGSProjectionRegistry:
    """Deterministic registry for ordered, replayable UGS projections.

    The registry is deliberately storage-agnostic. Persistence and worker leasing
    remain runtime concerns; this boundary guarantees that a projection sees
    validated states in strict session order and cannot silently cross sessions.
    """

    def __init__(self) -> None:
        self._projections: dict[str, Projection] = {}
        self._last_sequence: dict[str, int] = {}

    def register(self, name: str, projection: Projection) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("projection name must be non-empty")
        if normalized in self._projections:
            raise ValueError("PROJECTION_DUPLICATE")
        self._projections[normalized] = projection

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._projections))

    def apply(self, state: UGSState) -> ProjectionResult:
        previous = self._last_sequence.get(state.session_id)
        if previous is not None and state.sequence <= previous:
            raise ValueError("PROJECTION_SEQUENCE_REPLAY")
        applied: list[str] = []
        for name in self.names():
            self._projections[name](state)
            applied.append(name)
        self._last_sequence[state.session_id] = state.sequence
        return ProjectionResult(state.sequence, tuple(applied))

    def replay(self, states: Iterable[UGSState]) -> tuple[ProjectionResult, ...]:
        ordered = tuple(states)
        previous: tuple[str, int] | None = None
        for state in ordered:
            if previous is not None and (
                state.session_id != previous[0] or state.sequence <= previous[1]
            ):
                raise ValueError("PROJECTION_REPLAY_ORDER")
            previous = (state.session_id, state.sequence)
        return tuple(self.apply(state) for state in ordered)
