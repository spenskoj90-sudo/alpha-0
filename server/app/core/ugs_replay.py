from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
import json

from app.core.unified_game_state import UGSState


class DeterministicUGSReplay:
    """Canonical replay of validated UGS snapshots for regression tests."""

    def __init__(self, states: Iterable[UGSState]) -> None:
        self._states = tuple(states)
        self._validate_sequence()

    def _validate_sequence(self) -> None:
        previous: int | None = None
        session: str | None = None
        for state in self._states:
            if session is None:
                session = state.session_id
            elif state.session_id != session:
                raise ValueError("replay fixture must contain one session")
            if previous is not None and state.sequence <= previous:
                raise ValueError("replay fixture sequences must be strictly increasing")
            previous = state.sequence

    def states(self) -> tuple[UGSState, ...]:
        return self._states

    def canonical_bytes(self) -> bytes:
        payload = [state.model_dump(mode="json", by_alias=True, exclude_none=False) for state in self._states]
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def digest(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    def replay(self) -> tuple[UGSState, ...]:
        return tuple(UGSState.model_validate(item) for item in json.loads(self.canonical_bytes()))
