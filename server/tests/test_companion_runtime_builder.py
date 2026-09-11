from unittest.mock import MagicMock

import pytest

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


def test_builder_accepts_explicit_persistent_engine_without_opening_it():
    engine = MagicMock()

    runtime = build_companion_runtime(persistent_engine=engine)

    assert isinstance(runtime, CompanionRuntime)
    engine.connect.assert_not_called()


def test_builder_rejects_ambiguous_telemetry_configuration():
    telemetry = BoundedCompanionTelemetrySink(max_events=4)

    with pytest.raises(ValueError, match="COMPANION_TELEMETRY_CONFIGURATION_CONFLICT"):
        build_companion_runtime(telemetry=telemetry, persistent_engine=MagicMock())
