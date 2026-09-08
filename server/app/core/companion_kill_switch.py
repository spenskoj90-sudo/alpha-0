from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class CompanionKillSwitchState:
    active: bool


class CompanionKillSwitch:
    """Local fail-closed latch for Companion shutdown.

    The switch is process-local and requires no cloud dependency. Activation is
    terminal for the attached runtime/session until an explicit local reset.
    It never grants authorization or executes actions.
    """

    def __init__(self, *, active: bool = False) -> None:
        self._lock = Lock()
        self._active = active

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    def state(self) -> CompanionKillSwitchState:
        return CompanionKillSwitchState(active=self.active)

    def activate(self) -> None:
        with self._lock:
            self._active = True

    def reset(self) -> None:
        with self._lock:
            self._active = False

    def require_clear(self) -> None:
        if self.active:
            raise RuntimeError("Companion kill switch is active")
