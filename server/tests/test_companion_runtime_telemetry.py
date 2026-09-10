from app.core.companion_observability import BoundedCompanionTelemetrySink
from app.core.companion_telemetry_fanout import FanoutCompanionTelemetrySink
from app.core.companion_runtime_telemetry import build_companion_telemetry


def test_factory_builds_bounded_local_sink_by_default() -> None:
    sink = build_companion_telemetry()
    assert isinstance(sink, BoundedCompanionTelemetrySink)


def test_factory_preserves_injected_local_sink() -> None:
    local = BoundedCompanionTelemetrySink()
    assert build_companion_telemetry(local_sink=local) is local


def test_factory_composes_optional_persistent_sink() -> None:
    local = BoundedCompanionTelemetrySink()
    persistent = BoundedCompanionTelemetrySink()
    sink = build_companion_telemetry(local_sink=local, persistent_sink=persistent)

    assert isinstance(sink, FanoutCompanionTelemetrySink)
    assert sink.sink_count == 2
