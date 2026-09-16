from __future__ import annotations

from .companion_observability import CompanionTelemetrySink
from .companion_telemetry_fanout import FanoutCompanionTelemetrySink


def compose_companion_telemetry(
    local_sink: CompanionTelemetrySink,
    persistent_sink: CompanionTelemetrySink | None = None,
    provider_sink: CompanionTelemetrySink | None = None,
) -> CompanionTelemetrySink:
    """Compose local, persistent and optional provider sinks without runtime coupling."""

    sinks = tuple(
        sink for sink in (local_sink, persistent_sink, provider_sink) if sink is not None
    )
    if len(sinks) == 1:
        return local_sink
    return FanoutCompanionTelemetrySink(sinks)
