from __future__ import annotations

from .companion_observability import BoundedCompanionTelemetrySink, CompanionTelemetrySink
from .companion_persistent_runtime import build_persistent_companion_telemetry
from .companion_runtime import CompanionRuntime, CompanionRuntimeConfig
from .companion_telemetry_fanout import FanoutCompanionTelemetrySink
from .operational_companion_sink import OperationalCompanionTelemetrySink


def _default_runtime_telemetry(*, persistent_engine=None) -> CompanionTelemetrySink:
    """Compose bounded local/operator telemetry and optional PostgreSQL persistence."""
    operator = OperationalCompanionTelemetrySink()
    if persistent_engine is not None:
        persistent_composition = build_persistent_companion_telemetry(persistent_engine)
        return FanoutCompanionTelemetrySink((persistent_composition, operator))
    return FanoutCompanionTelemetrySink((BoundedCompanionTelemetrySink(), operator))


def build_companion_runtime(
    *,
    config: CompanionRuntimeConfig | None = None,
    telemetry: CompanionTelemetrySink | None = None,
    persistent_engine=None,
) -> CompanionRuntime:
    """Construct a Companion runtime with bounded operator telemetry by default.

    Persistence remains explicit: callers must provide ``persistent_engine`` to
    compose the existing PostgreSQL sink. Explicit telemetry remains fully
    caller-owned and is never silently wrapped. No database/provider connection
    is created implicitly by local/default runtime construction.
    """
    if telemetry is not None and persistent_engine is not None:
        raise ValueError("COMPANION_TELEMETRY_CONFIGURATION_CONFLICT")
    selected_telemetry = telemetry if telemetry is not None else _default_runtime_telemetry(persistent_engine=persistent_engine)
    return CompanionRuntime(
        config=config,
        telemetry=selected_telemetry,
    )
