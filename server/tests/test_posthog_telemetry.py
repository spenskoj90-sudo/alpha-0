from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.companion_observability import CompanionTelemetryEvent
from app.core.posthog_telemetry import (
    PostHogCompanionTelemetrySink,
    PostHogConfig,
    configured_posthog_sink,
)


class CaptureTransport:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.payloads: list[dict] = []

    def capture(self, payload: dict) -> None:
        if self.fail:
            raise RuntimeError("provider down")
        self.payloads.append(payload)


def config() -> PostHogConfig:
    return PostHogConfig(
        project_key="phc_test_project_key",
        region="eu",
        environment="staging",
        release="1.0.0-rc1",
        source_sha="a" * 40,
    )


def test_posthog_sink_sends_only_bounded_release_correlated_properties() -> None:
    transport = CaptureTransport()
    sink = PostHogCompanionTelemetrySink(config(), transport)
    event = CompanionTelemetryEvent.create(
        "companion.runtime.degraded",
        datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        {
            "reason": "heartbeat_timeout",
            "latency_ms": 42.5,
            "device_id": "must-not-leave-process",
            "user_id": "must-not-leave-process",
            "request_id": "must-not-leave-process",
        },
    )

    sink.record(event)

    assert sink.delivered_events == 1
    assert sink.dropped_events == 0
    assert len(transport.payloads) == 1
    payload = transport.payloads[0]
    assert payload["event"] == "companion.runtime.degraded"
    assert payload["timestamp"] == "2026-09-16T12:00:00+00:00"
    properties = payload["properties"]
    assert properties == {
        "distinct_id": "sentinel-runtime",
        "$process_person_profile": False,
        "environment": "staging",
        "release": "1.0.0-rc1",
        "source_sha": "a" * 40,
        "reason": "heartbeat_timeout",
        "latency_ms": 42.5,
    }


def test_posthog_provider_failure_isolated_from_companion_runtime() -> None:
    sink = PostHogCompanionTelemetrySink(config(), CaptureTransport(fail=True))
    sink.record(
        CompanionTelemetryEvent.create(
            "companion.runtime.started",
            datetime.now(UTC),
        )
    )
    assert sink.delivered_events == 0
    assert sink.dropped_events == 1


def test_posthog_region_is_strictly_allowlisted() -> None:
    with pytest.raises(ValueError, match="POSTHOG_REGION_INVALID"):
        PostHogConfig(
            project_key="phc_test",
            region="https://127.0.0.1",
            environment="staging",
            release="rc1",
            source_sha="a" * 40,
        )
    with pytest.raises(ValueError, match="POSTHOG_REGION_INVALID"):
        PostHogConfig(
            project_key="phc_test",
            region="example.com",
            environment="staging",
            release="rc1",
            source_sha="a" * 40,
        )


def test_posthog_is_disabled_by_default_and_fails_closed_on_bad_activation(monkeypatch) -> None:
    for name in (
        "SENTINEL_POSTHOG_ENABLED",
        "SENTINEL_POSTHOG_PROJECT_KEY",
        "SENTINEL_POSTHOG_REGION",
        "SENTINEL_RELEASE",
        "SENTINEL_SOURCE_SHA",
    ):
        monkeypatch.delenv(name, raising=False)
    assert configured_posthog_sink() is None

    monkeypatch.setenv("SENTINEL_POSTHOG_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_ENV", "staging")
    with pytest.raises(RuntimeError, match="POSTHOG_NOT_CONFIGURED"):
        configured_posthog_sink()

    monkeypatch.setenv("SENTINEL_POSTHOG_PROJECT_KEY", "phc_test")
    monkeypatch.setenv("SENTINEL_RELEASE", "rc1")
    monkeypatch.setenv("SENTINEL_SOURCE_SHA", "b" * 40)
    monkeypatch.setenv("SENTINEL_POSTHOG_REGION", "private-network")
    with pytest.raises(RuntimeError, match="POSTHOG_REGION_INVALID"):
        configured_posthog_sink()

    monkeypatch.setenv("SENTINEL_POSTHOG_REGION", "us")
    monkeypatch.setenv("SENTINEL_ENV", "production")
    with pytest.raises(RuntimeError, match="POSTHOG_STAGING_ONLY"):
        configured_posthog_sink()
