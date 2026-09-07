from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.companion_protocol import CompanionMode
from app.core.companion_runtime import CompanionRuntime, CompanionRuntimeConfig


T0 = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_start_and_heartbeat_keep_runtime_active() -> None:
    runtime = CompanionRuntime()
    runtime.start(T0)
    assert runtime.mode is CompanionMode.ACTIVE
    assert runtime.watchdog(T0 + timedelta(seconds=9)) is CompanionMode.ACTIVE


def test_watchdog_degrades_after_timeout_and_heartbeat_recovers() -> None:
    runtime = CompanionRuntime(CompanionRuntimeConfig(heartbeat_timeout=timedelta(seconds=5)))
    runtime.start(T0)
    assert runtime.watchdog(T0 + timedelta(seconds=5)) is CompanionMode.ACTIVE
    assert runtime.watchdog(T0 + timedelta(seconds=5, microseconds=1)) is CompanionMode.DEGRADED
    runtime.record_heartbeat(T0 + timedelta(seconds=6))
    assert runtime.mode is CompanionMode.ACTIVE


def test_stop_is_terminal_until_new_runtime_start() -> None:
    runtime = CompanionRuntime()
    runtime.start(T0)
    runtime.stop()
    assert runtime.watchdog(T0 + timedelta(minutes=1)) is CompanionMode.STOPPED
    runtime.record_heartbeat(T0 + timedelta(minutes=1, seconds=1))
    assert runtime.mode is CompanionMode.STOPPED
    runtime.start(T0 + timedelta(minutes=2))
    assert runtime.mode is CompanionMode.ACTIVE


def test_heartbeat_timestamps_are_monotonic_and_timezone_aware() -> None:
    runtime = CompanionRuntime()
    runtime.start(T0)
    with pytest.raises(ValueError):
        runtime.record_heartbeat(T0 - timedelta(seconds=1))
    with pytest.raises(ValueError):
        runtime.record_heartbeat(T0.replace(tzinfo=None))


def test_latency_observation_is_measurable_and_non_negative() -> None:
    runtime = CompanionRuntime()
    assert runtime.observe_latency(T0, T0 + timedelta(milliseconds=37)) == 37.0
    assert runtime.last_latency_ms == 37.0
    with pytest.raises(ValueError):
        runtime.observe_latency(T0 + timedelta(seconds=1), T0)
    with pytest.raises(ValueError):
        runtime.observe_latency(T0.replace(tzinfo=None), T0)


def test_reconnect_backoff_is_bounded_and_exponential() -> None:
    runtime = CompanionRuntime(
        CompanionRuntimeConfig(
            reconnect_initial=timedelta(seconds=1), reconnect_max=timedelta(seconds=5)
        )
    )
    assert runtime.reconnect_delay() == timedelta(seconds=1)
    assert runtime.register_reconnect_attempt() == timedelta(seconds=1)
    assert runtime.register_reconnect_attempt() == timedelta(seconds=2)
    assert runtime.register_reconnect_attempt() == timedelta(seconds=4)
    assert runtime.register_reconnect_attempt() == timedelta(seconds=5)
    assert runtime.reconnect_delay() == timedelta(seconds=5)


def test_config_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError):
        CompanionRuntimeConfig(heartbeat_timeout=timedelta(0))
    with pytest.raises(ValueError):
        CompanionRuntimeConfig(
            reconnect_initial=timedelta(seconds=2), reconnect_max=timedelta(seconds=1)
        )
