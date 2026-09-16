from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.core.runtime_maintenance import (
    RuntimeMaintenanceService,
    install_runtime_maintenance,
    runtime_maintenance_enabled,
    runtime_maintenance_interval_from_env,
)


class FakeApp:
    def __init__(self) -> None:
        self.state = SimpleNamespace()
        self.original_entered = False
        self.original_exited = False

        @asynccontextmanager
        async def original_lifespan(_app):
            self.original_entered = True
            try:
                yield {"original": True}
            finally:
                self.original_exited = True

        self.original_lifespan = original_lifespan
        self.router = SimpleNamespace(lifespan_context=original_lifespan)


def test_runtime_maintenance_defaults_only_for_managed_environments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_RUNTIME_MAINTENANCE_ENABLED", raising=False)
    assert runtime_maintenance_enabled("production") is True
    assert runtime_maintenance_enabled("staging") is True
    assert runtime_maintenance_enabled("development") is False
    assert runtime_maintenance_enabled("test") is False


def test_runtime_maintenance_boolean_and_interval_are_fail_closed() -> None:
    assert runtime_maintenance_enabled("development", "true") is True
    assert runtime_maintenance_enabled("production", "off") is False
    with pytest.raises(RuntimeError, match="must be a boolean"):
        runtime_maintenance_enabled("production", "sometimes")

    assert runtime_maintenance_interval_from_env("300") == 300
    assert runtime_maintenance_interval_from_env("86400") == 86400
    with pytest.raises(RuntimeError, match="outside the allowed safety range"):
        runtime_maintenance_interval_from_env("299")
    with pytest.raises(RuntimeError, match="must be an integer"):
        runtime_maintenance_interval_from_env("six-hours")


def test_service_runs_immediately_and_stops_without_waiting() -> None:
    calls: list[tuple[object, int]] = []

    def purge(engine, *, batch_size):
        calls.append((engine, batch_size))
        return {"sessions": 2}

    engine = object()
    service = RuntimeMaintenanceService(
        engine,  # type: ignore[arg-type]
        interval_seconds=300,
        batch_size=100,
        purge=purge,
    )
    service.start()
    try:
        assert calls == [(engine, 100)]
        assert service.last_result == {"sessions": 2}
        assert service.last_error is None
    finally:
        service.stop()


def test_service_isolates_purge_failure() -> None:
    def purge(_engine, *, batch_size):
        assert batch_size == 100
        raise RuntimeError("database unavailable")

    service = RuntimeMaintenanceService(
        object(),  # type: ignore[arg-type]
        interval_seconds=300,
        batch_size=100,
        purge=purge,
    )
    service.run_once()
    assert service.last_result is None
    assert service.last_error == "RuntimeError"


def test_install_composes_supported_lifespan_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTINEL_RUNTIME_MAINTENANCE_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_RUNTIME_MAINTENANCE_INTERVAL_SECONDS", "300")
    monkeypatch.setenv("SENTINEL_RETENTION_BATCH_SIZE", "100")

    lifecycle: list[str] = []
    monkeypatch.setattr(RuntimeMaintenanceService, "start", lambda self: lifecycle.append("maintenance-start"))
    monkeypatch.setattr(RuntimeMaintenanceService, "stop", lambda self: lifecycle.append("maintenance-stop"))

    app = FakeApp()
    service = install_runtime_maintenance(app, object(), environment="staging")  # type: ignore[arg-type]
    assert service is not None
    assert app.state.runtime_maintenance is service
    assert app.router.lifespan_context is not app.original_lifespan

    async def exercise_lifespan() -> None:
        async with app.router.lifespan_context(app) as state:
            assert state == {"original": True}
            assert app.original_entered is True
            assert lifecycle == ["maintenance-start"]

    asyncio.run(exercise_lifespan())
    assert app.original_exited is True
    assert lifecycle == ["maintenance-start", "maintenance-stop"]

    disabled = FakeApp()
    monkeypatch.setenv("SENTINEL_RUNTIME_MAINTENANCE_ENABLED", "false")
    assert install_runtime_maintenance(disabled, object(), environment="production") is None  # type: ignore[arg-type]
    assert disabled.state.runtime_maintenance is None
    assert disabled.router.lifespan_context is disabled.original_lifespan
