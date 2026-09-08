from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .companion_kill_switch import CompanionKillSwitch
from .companion_protocol import CompanionMode


@dataclass(frozen=True, slots=True)
class CompanionRuntimeConfig:
    heartbeat_timeout: timedelta = timedelta(seconds=10)
    reconnect_initial: timedelta = timedelta(seconds=1)
    reconnect_max: timedelta = timedelta(seconds=60)

    def __post_init__(self) -> None:
        if self.heartbeat_timeout <= timedelta(0):
            raise ValueError("heartbeat_timeout must be positive")
        if self.reconnect_initial <= timedelta(0):
            raise ValueError("reconnect_initial must be positive")
        if self.reconnect_max < self.reconnect_initial:
            raise ValueError("reconnect_max must be >= reconnect_initial")


class CompanionRuntime:
    """Transport-neutral lifecycle/watchdog state; never authorizes or executes actions."""

    def __init__(
        self,
        config: CompanionRuntimeConfig | None = None,
        kill_switch: CompanionKillSwitch | None = None,
    ) -> None:
        self.config = config or CompanionRuntimeConfig()
        self.kill_switch = kill_switch or CompanionKillSwitch()
        self.mode = CompanionMode.STOPPED
        self.last_heartbeat: datetime | None = None
        self.reconnect_attempts = 0
        self.last_latency_ms: float | None = None

    def start(self, now: datetime | None = None) -> None:
        self.kill_switch.require_clear()
        self.mode = CompanionMode.ACTIVE
        self.reconnect_attempts = 0
        self.record_heartbeat(now)

    def record_heartbeat(self, now: datetime | None = None) -> None:
        self.kill_switch.require_clear()
        timestamp = self.timestamp_utc(now)
        if self.last_heartbeat is not None and timestamp < self.last_heartbeat:
            raise ValueError("heartbeat timestamp must be monotonic")
        self.last_heartbeat = timestamp
        if self.mode is not CompanionMode.STOPPED:
            self.mode = CompanionMode.ACTIVE

    def observe_latency(self, sent_at: datetime, received_at: datetime) -> float:
        start = self.timestamp_utc(sent_at)
        end = self.timestamp_utc(received_at)
        if end < start:
            raise ValueError("received_at must be >= sent_at")
        latency_ms = (end - start).total_seconds() * 1000
        self.last_latency_ms = latency_ms
        return latency_ms

    def watchdog(self, now: datetime | None = None) -> CompanionMode:
        if self.kill_switch.active:
            self.mode = CompanionMode.STOPPED
            return self.mode
        if self.mode is CompanionMode.STOPPED:
            return self.mode
        timestamp = self.timestamp_utc(now)
        if self.last_heartbeat is None or timestamp - self.last_heartbeat > self.config.heartbeat_timeout:
            self.mode = CompanionMode.DEGRADED
        return self.mode

    def degrade(self) -> None:
        """Mark transport health degraded without making a stop or authorization decision."""
        if self.kill_switch.active:
            self.mode = CompanionMode.STOPPED
            return
        if self.mode is not CompanionMode.STOPPED:
            self.mode = CompanionMode.DEGRADED

    def activate_kill_switch(self) -> None:
        """Stop Companion locally and prevent reconnect/start until reset."""
        self.kill_switch.activate()
        self.mode = CompanionMode.STOPPED

    def reset_kill_switch(self) -> None:
        """Explicitly clear the local latch; the runtime remains stopped until start()."""
        self.kill_switch.reset()
        self.mode = CompanionMode.STOPPED

    def stop(self) -> None:
        self.mode = CompanionMode.STOPPED

    def reconnect_delay(self) -> timedelta:
        if self.kill_switch.active:
            raise RuntimeError("Companion kill switch is active")
        exponent = min(self.reconnect_attempts, 10)
        delay = self.config.reconnect_initial * (2**exponent)
        return min(delay, self.config.reconnect_max)

    def register_reconnect_attempt(self) -> timedelta:
        delay = self.reconnect_delay()
        self.reconnect_attempts += 1
        return delay

    @staticmethod
    def timestamp_utc(value: datetime | None) -> datetime:
        timestamp = value or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return timestamp.astimezone(timezone.utc)
