from unittest.mock import MagicMock

from app.core.companion_persistent_runtime import build_persistent_companion_telemetry


def test_persistent_runtime_factory_keeps_database_dependency_explicit() -> None:
    engine = MagicMock()
    sink = build_persistent_companion_telemetry(engine)
    assert sink is not None
    engine.begin.assert_not_called()
