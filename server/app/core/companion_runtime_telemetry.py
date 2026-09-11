from __future__ import annotations

from .companion_observability import BoundedCompanionTelemetrySink, CompanionTelemetrySink
from .companion_telemetry_composition import compose_companion_telemetry


def build_companion_telemetry(
    *,
    local_sink: CompanionTelemetrySink | None = None,
    persistent_sink: CompanionTelemetrySink | None = None,
) -> CompanionTelemetrySink:
    """Build bounded local telemetry with an optional persistent fanout sink."""

    local = local_sink or BoundedCompanionTelemetrySink()
    return compose_companion_telemetry(local, persistent_sink)
