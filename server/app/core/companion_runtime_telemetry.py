from __future__ import annotations

from .companion_observability import BoundedCompanionTelemetrySink, CompanionTelemetrySink
from .companion_telemetry_composition import compose_companion_telemetry
from .posthog_telemetry import configured_posthog_sink


def build_companion_telemetry(
    *,
    local_sink: CompanionTelemetrySink | None = None,
    persistent_sink: CompanionTelemetrySink | None = None,
    provider_sink: CompanionTelemetrySink | None = None,
) -> CompanionTelemetrySink:
    """Build bounded local telemetry with optional durable/provider fanout.

    PostHog is disabled by default. When no explicit provider sink is supplied,
    environment configuration may enable the privacy-bounded staging adapter.
    """

    local = local_sink or BoundedCompanionTelemetrySink()
    selected_provider = provider_sink if provider_sink is not None else configured_posthog_sink()
    return compose_companion_telemetry(local, persistent_sink, selected_provider)
