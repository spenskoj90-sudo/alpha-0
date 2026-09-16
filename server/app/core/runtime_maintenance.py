from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from threading import Event, Lock, Thread
from typing import Any

from sqlalchemy import Engine

from app.core.retention import purge_expired_runtime_data, retention_batch_size_from_env

LOGGER = logging.getLogger("sentinel.runtime_maintenance")

DEFAULT_INTERVAL_SECONDS = 6 * 60 * 60
MIN_INTERVAL_SECONDS = 5 * 60
MAX_INTERVAL_SECONDS = 24 * 60 * 60


def runtime_maintenance_enabled(environment: str, value: str | None = None) -> bool:
    raw = value if value is not None else os.getenv("SENTINEL_RUNTIME_MAINTENANCE_ENABLED")
    if raw is None:
        return environment.lower() in {"production", "staging"}
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError("SENTINEL_RUNTIME_MAINTENANCE_ENABLED must be a boolean")


def runtime_maintenance_interval_from_env(value: str | None = None) -> int:
    raw = value if value is not None else os.getenv(
        "SENTINEL_RUNTIME_MAINTENANCE_INTERVAL_SECONDS",
        str(DEFAULT_INTERVAL_SECONDS),
    )
    try:
        interval = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("SENTINEL_RUNTIME_MAINTENANCE_INTERVAL_SECONDS must be an integer") from exc
    if not MIN_INTERVAL_SECONDS <= interval <= MAX_INTERVAL_SECONDS:
        raise RuntimeError("SENTINEL_RUNTIME_MAINTENANCE_INTERVAL_SECONDS is outside the allowed safety range")
    return interval


class RuntimeMaintenanceService:
    """Small in-process scheduler for bounded transient-data maintenance.

    The database layer owns distributed serialization through a transaction advisory
    lock, so multiple process-local schedulers are safe. Maintenance failures are
    isolated from request serving and retried on the next interval.
    """

    def __init__(
        self,
        engine: Engine,
        *,
        interval_seconds: int,
        batch_size: int,
        purge: Callable[..., Mapping[str, int]] = purge_expired_runtime_data,
    ) -> None:
        self.engine = engine
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self._purge = purge
        self._stop = Event()
        self._thread: Thread | None = None
        self._lifecycle_lock = Lock()
        self.last_result: dict[str, int] | None = None
        self.last_error: str | None = None

    def run_once(self) -> None:
        try:
            result = self._purge(self.engine, batch_size=self.batch_size)
            self.last_result = dict(result)
            self.last_error = None
            LOGGER.info("runtime maintenance completed deleted=%s", sum(self.last_result.values()))
        except Exception as exc:  # maintenance must never take the API down
            self.last_error = type(exc).__name__
            LOGGER.exception("runtime maintenance failed")

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.run_once()

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self.run_once()
            self._thread = Thread(
                target=self._loop,
                name="sentinel-runtime-maintenance",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lifecycle_lock:
            thread = self._thread
            self._thread = None
            self._stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)


def install_runtime_maintenance(app: Any, engine: Engine | None, *, environment: str) -> RuntimeMaintenanceService | None:
    if engine is None or not runtime_maintenance_enabled(environment):
        app.state.runtime_maintenance = None
        return None

    service = RuntimeMaintenanceService(
        engine,
        interval_seconds=runtime_maintenance_interval_from_env(),
        batch_size=retention_batch_size_from_env(),
    )
    app.state.runtime_maintenance = service
    app.add_event_handler("startup", service.start)
    app.add_event_handler("shutdown", service.stop)
    return service
