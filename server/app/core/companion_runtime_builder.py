from __future__ import annotations

from .companion_observability import CompanionTelemetrySink
from .companion_runtime import CompanionRuntime, CompanionRuntimeConfig
from .companion_runtime_telemetry import build_companion_telemetry


def build_companion_runtime(
    *,
    config: CompanionRuntimeConfig | None = None,
    telemetry: CompanionTelemetrySink | None = None,
) -> CompanionRuntime:
    """Construct a Companion runtime with bounded telemetry by default."""

    return CompanionRuntime(
        config=config,
        telemetry=telemetry if telemetry is not None else build_companion_telemetry(),
    )
