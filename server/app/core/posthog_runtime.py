from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from .posthog_telemetry import PostHogCompanionTelemetrySink, configured_posthog_sink


def install_posthog_runtime_telemetry(app: Any) -> PostHogCompanionTelemetrySink | None:
    """Attach optional staging delivery to real ASGI startup, never to requests.

    Config validation remains fail-closed. Provider outages are isolated by the
    bounded sink, and its HTTPS call runs off the event loop. No user/session
    data is observed; the single event contains static release identity only.
    """
    sink = configured_posthog_sink()
    app.state.posthog_runtime_telemetry = sink
    if sink is None:
        return None

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def telemetry_lifespan(application: Any):
        async with original_lifespan(application) as state:
            await asyncio.to_thread(sink.record_runtime_started)
            yield state

    app.router.lifespan_context = telemetry_lifespan
    return sink
