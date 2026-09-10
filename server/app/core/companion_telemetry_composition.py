from __future__ import annotations

from .companion_observability import CompanionTelemetrySink
from .companion_telemetry_fanout import FanoutCompanionTelemetrySink


def compose_companion_telemetry(
    local_sink: CompanionTelemetrySink,
    persistent_sink: CompanionTelemetrySink | None = None,
) -> CompanionTelemetrySink:
    """Compose local and optional persistent sinks without coupling runtime code to storage."""

    if persistent_sink is None:
        return local_sink
    return FanoutCompanionTelemetrySink((local_sink, persistent_sink))
