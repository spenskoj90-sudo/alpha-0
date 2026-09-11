from app.core.companion_observability import BoundedCompanionTelemetrySink
from app.core.companion_runtime import CompanionRuntime, CompanionRuntimeConfig
from app.core.companion_runtime_builder import build_companion_runtime


def test_builder_returns_runtime_with_bounded_default_telemetry():
    runtime = build_companion_runtime()

    assert isinstance(runtime, CompanionRuntime)
    assert isinstance(runtime.telemetry, BoundedCompanionTelemetrySink)


def test_builder_preserves_explicit_telemetry_and_config():
    telemetry = BoundedCompanionTelemetrySink(max_events=4)
    config = CompanionRuntimeConfig()
    runtime = build_companion_runtime(config=config, telemetry=telemetry)

    assert runtime.config is config
    assert runtime.telemetry is telemetry
