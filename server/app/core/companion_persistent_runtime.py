from __future__ import annotations

from .companion_observability import CompanionTelemetrySink
from .companion_persistent_observability import PostgresCompanionTelemetrySink
from .companion_runtime_telemetry import build_companion_telemetry


def build_persistent_companion_telemetry(
    engine,
    *,
    local_sink: CompanionTelemetrySink | None = None,
) -> CompanionTelemetrySink:
    """Compose bounded local telemetry with the existing PostgreSQL sink.

    The database engine is explicit so persistence cannot appear implicitly in
    tests, local development, or runtime construction. The returned fanout
    retains the bounded local sink and the existing retention policy.
    """
    persistent = PostgresCompanionTelemetrySink(engine)
    return build_companion_telemetry(
        local_sink=local_sink,
        persistent_sink=persistent,
    )
