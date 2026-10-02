from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.core.posthog_telemetry import PostHogCompanionTelemetrySink, PostHogConfig
from app.core.posthog_runtime import install_posthog_runtime_telemetry


class CaptureTransport:
    def __init__(self, *, fail=False):
        self.payloads = []
        self.fail = fail

    def capture(self, payload):
        if self.fail:
            raise RuntimeError("provider down")
        self.payloads.append(payload)


def make_app():
    app = SimpleNamespace(state=SimpleNamespace(), lifecycle=[])
    @asynccontextmanager
    async def original(_app):
        app.lifecycle.append("start")
        try:
            yield {"preserved": True}
        finally:
            app.lifecycle.append("stop")
    app.router = SimpleNamespace(lifespan_context=original)
    return app, original


def make_sink(transport):
    return PostHogCompanionTelemetrySink(
        PostHogConfig(project_key="phc_test", region="eu", environment="staging",
                      release="1.0.0-rc2", source_sha="a" * 40), transport
    )


def test_disabled_install_preserves_lifespan_and_has_no_network(monkeypatch):
    app, original = make_app()
    monkeypatch.setattr("app.core.posthog_runtime.configured_posthog_sink", lambda: None)
    assert install_posthog_runtime_telemetry(app) is None
    assert app.router.lifespan_context is original
    assert app.state.posthog_runtime_telemetry is None


@pytest.mark.parametrize("fail", [False, True])
def test_actual_lifespan_emits_once_and_provider_failure_does_not_block_serving(monkeypatch, fail):
    transport = CaptureTransport(fail=fail)
    sink = make_sink(transport)
    app, _ = make_app()
    monkeypatch.setattr("app.core.posthog_runtime.configured_posthog_sink", lambda: sink)
    assert install_posthog_runtime_telemetry(app) is sink

    async def run():
        async with app.router.lifespan_context(app) as state:
            assert state == {"preserved": True}
            assert app.lifecycle == ["start"]
    asyncio.run(run())
    assert app.lifecycle == ["start", "stop"]
    assert sink.delivered_events == (0 if fail else 1)
    assert sink.dropped_events == (1 if fail else 0)
    if not fail:
        assert len(transport.payloads) == 1
        payload = transport.payloads[0]
        assert payload["event"] == "core.runtime.started"
        assert payload["properties"] == {
            "distinct_id": "sentinel-runtime",
            "$process_person_profile": False,
            "$geoip_disable": True,
            "environment": "staging",
            "release": "1.0.0-rc2",
            "source_sha": "a" * 40,
        }
