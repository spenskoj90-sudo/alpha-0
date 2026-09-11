from __future__ import annotations

from .companion_observability import CompanionTelemetrySink
from .companion_persistent_runtime import build_persistent_companion_telemetry
from .companion_runtime import CompanionRuntime, CompanionRuntimeConfig
from .companion_runtime_telemetry import build_companion_telemetry


def build_companion_runtime(
    *,
    config: CompanionRuntimeConfig | None = None,
    telemetry: CompanionTelemetrySink | None = None,
    persistent_engine=None,
) -> CompanionRuntime:
    """Construct a Companion runtime with bounded telemetry by default.

    Persistence is explicit: callers must provide ``persistent_engine`` to
    compose the existing PostgreSQL sink. No database connection is created
    implicitly by local/default runtime construction.
    """
    if telemetry is not None and persistent_engine is not None:
        raise ValueError("COMPANION_TELEMETRY_CONFIGURATION_CONFLICT")
    if persistent_engine is not None:
        selected_telemetry = build_persistent_companion_telemetry(persistent_engine)
    else:
        selected_telemetry = telemetry if telemetry is not None else build_companion_telemetry()
    return CompanionRuntime(
        config=config,
        telemetry=selected_telemetry,
    )
