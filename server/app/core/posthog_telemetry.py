from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.companion_observability import CompanionTelemetryEvent, CompanionTelemetrySink

_MAX_RESPONSE_BYTES = 65_536
_ALLOWED_ATTRIBUTES = frozenset(
    {
        "mode",
        "reason",
        "state",
        "status",
        "outcome",
        "message_type",
        "latency_class",
        "latency_ms",
        "attempt",
        "delay_ms",
        "event_type",
    }
)
_SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
_RELEASE = re.compile(r"^[A-Za-z0-9._:+-]{1,128}$")
_ENVIRONMENT = re.compile(r"^[a-z0-9_-]{1,32}$")
_POSTHOG_REGIONS = frozenset({"us", "eu"})
_POSTHOG_US_CAPTURE = "https://us.i.posthog.com/capture/"
_POSTHOG_EU_CAPTURE = "https://eu.i.posthog.com/capture/"


class PostHogTransport(Protocol):
    def capture(self, payload: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class PostHogConfig:
    project_key: str = field(repr=False)
    region: str
    environment: str
    release: str
    source_sha: str

    def __post_init__(self) -> None:
        if not self.project_key or len(self.project_key) > 256:
            raise ValueError("POSTHOG_PROJECT_KEY_INVALID")
        if self.region not in _POSTHOG_REGIONS:
            raise ValueError("POSTHOG_REGION_INVALID")
        if not _ENVIRONMENT.fullmatch(self.environment):
            raise ValueError("POSTHOG_ENVIRONMENT_INVALID")
        if self.environment != "staging":
            raise ValueError("POSTHOG_STAGING_ONLY")
        if not _RELEASE.fullmatch(self.release):
            raise ValueError("POSTHOG_RELEASE_INVALID")
        if not _SOURCE_SHA.fullmatch(self.source_sha):
            raise ValueError("POSTHOG_SOURCE_SHA_INVALID")


class PostHogHttpTransport:
    def __init__(self, config: PostHogConfig, *, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 15:
            raise ValueError("POSTHOG_TIMEOUT_INVALID")
        self._config = config
        self._timeout_seconds = timeout_seconds

    def capture(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        # Never construct an outbound URL from environment- or request-controlled
        # text. Region selection chooses one of two literal provider endpoints,
        # eliminating an SSRF surface while retaining PostHog US/EU support.
        endpoint = _POSTHOG_EU_CAPTURE if self._config.region == "eu" else _POSTHOG_US_CAPTURE
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "sentinel-core/posthog-adapter",
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise RuntimeError(f"POSTHOG_HTTP_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("POSTHOG_UNAVAILABLE") from exc
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise RuntimeError("POSTHOG_RESPONSE_TOO_LARGE")


class PostHogCompanionTelemetrySink(CompanionTelemetrySink):
    """Fail-isolated, privacy-bounded staging telemetry sink.

    No user/device/session/game identity is sent. PostHog receives only the
    Companion event name, exact release correlation, and a small allowlist of
    operational properties. A provider outage never interrupts Core serving.
    """

    def __init__(self, config: PostHogConfig, transport: PostHogTransport | None = None) -> None:
        self.config = config
        self._transport = transport or PostHogHttpTransport(config)
        self._lock = Lock()
        self._delivered = 0
        self._dropped = 0

    @property
    def delivered_events(self) -> int:
        with self._lock:
            return self._delivered

    @property
    def dropped_events(self) -> int:
        with self._lock:
            return self._dropped

    def record(self, event: CompanionTelemetryEvent) -> None:
        properties: dict[str, str | int | float | bool] = {
            "distinct_id": "sentinel-runtime",
            "$process_person_profile": False,
            "environment": self.config.environment,
            "release": self.config.release,
            "source_sha": self.config.source_sha,
        }
        for key, value in event.attributes:
            if key in _ALLOWED_ATTRIBUTES:
                properties[key] = value
        payload = {
            "api_key": self.config.project_key,
            "event": event.name,
            "timestamp": event.observed_at.isoformat(),
            "properties": properties,
        }
        try:
            self._transport.capture(payload)
        except Exception:
            with self._lock:
                self._dropped += 1
            return
        with self._lock:
            self._delivered += 1


def configured_posthog_sink() -> PostHogCompanionTelemetrySink | None:
    if not _strict_env_bool("SENTINEL_POSTHOG_ENABLED", default=False):
        return None
    required = {
        "project_key": os.getenv("SENTINEL_POSTHOG_PROJECT_KEY", ""),
        "release": os.getenv("SENTINEL_RELEASE", ""),
        "source_sha": os.getenv("SENTINEL_SOURCE_SHA", ""),
    }
    if any(not value for value in required.values()):
        raise RuntimeError("POSTHOG_NOT_CONFIGURED")
    try:
        config = PostHogConfig(
            project_key=required["project_key"],
            region=os.getenv("SENTINEL_POSTHOG_REGION", "us").strip().lower(),
            environment=os.getenv("SENTINEL_ENV", "development").strip().lower(),
            release=required["release"],
            source_sha=required["source_sha"].strip().lower(),
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return PostHogCompanionTelemetrySink(config)


def _strict_env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"{name}_INVALID")
