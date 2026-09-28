from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHA40 = re.compile(r"^[0-9a-f]{40}$")

def _read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")

def _read_json(relative: str) -> dict[str, Any]:
    return json.loads(_read_text(relative))

def _source_sha() -> str:
    value = os.getenv("SENTINEL_SOURCE_SHA", "").strip().lower()
    return value if SHA40.fullmatch(value) else "UNKNOWN"

def _configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())

def project_state() -> dict[str, Any]:
    ux = _read_json("design/user-visible-acceptance.v1.json")
    design = _read_json("design/sentinel-design-system.v3.json")
    return {
        "schema": "sentinel.control-bridge.project-state.v1",
        "version": _read_text("VERSION").strip(),
        "sourceSha": _source_sha(),
        "environment": os.getenv("SENTINEL_ENV", "unknown").strip().lower() or "unknown",
        "design": {
            "revision": design.get("revision"),
            "status": design.get("status"),
            "referenceSha": design.get("designReference", {}).get("sha"),
            "productionParityClaimed": ux.get("designReference", {}).get("productionParityClaimed"),
        },
        "surfaces": [
            {
                "id": item.get("id"),
                "engineeringState": item.get("engineeringState"),
                "ownerVisible": item.get("ownerVisible"),
                "ownerVisualAccepted": bool(item.get("ownerVisualAccepted")),
                "ready": bool(item.get("ready")),
            }
            for item in ux.get("surfaces", [])
        ],
    }

def provider_state() -> dict[str, Any]:
    checks = {
        "openai": ("OPENAI_API_KEY",),
        "resend": ("RESEND_API_KEY",),
        "stripe": ("STRIPE_SECRET_KEY",),
        "posthog": ("POSTHOG_API_KEY", "NEXT_PUBLIC_POSTHOG_KEY"),
        "sentry": ("SENTRY_DSN", "SENTRY_AUTH_TOKEN"),
        "googleOidc": ("SENTINEL_GOOGLE_CLIENT_ID",),
        "telegramOidc": ("SENTINEL_TELEGRAM_CLIENT_ID",),
        "vkOidc": ("SENTINEL_VK_CLIENT_ID",),
    }
    return {
        "schema": "sentinel.control-bridge.provider-state.v1",
        "providers": {
            key: {"configured": any(_configured(name) for name in names)}
            for key, names in checks.items()
        },
    }

def _probe(name: str, base_url: str, path: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    if not base_url:
        return {"name": name, "configured": False, "status": "UNCONFIGURED"}
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"User-Agent": "sentinel-control-bridge/1"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            code = int(getattr(response, "status", 0))
        return {"name": name, "configured": True, "status": "HEALTHY" if 200 <= code < 400 else "DEGRADED", "httpStatus": code}
    except urllib.error.HTTPError as exc:
        return {"name": name, "configured": True, "status": "DEGRADED", "httpStatus": int(exc.code)}
    except Exception as exc:
        return {"name": name, "configured": True, "status": "UNREACHABLE", "errorType": type(exc).__name__}

def runtime_health() -> dict[str, Any]:
    return {
        "schema": "sentinel.control-bridge.runtime-health.v1",
        "sourceSha": _source_sha(),
        "checks": [
            _probe("core", os.getenv("SENTINEL_CORE_URL", ""), "/healthz"),
            _probe("web", os.getenv("SENTINEL_WEB_URL", ""), "/"),
        ],
    }

def release_readiness() -> dict[str, Any]:
    ux = _read_json("design/user-visible-acceptance.v1.json")
    task_text = _read_text("docs/TASKS.md")
    issue_ids = sorted({int(value) for value in re.findall(r"- \[ \] \*\*#(\d+)", task_text)})
    surfaces = ux.get("surfaces", [])
    return {
        "schema": "sentinel.control-bridge.release-readiness.v1",
        "sourceSha": _source_sha(),
        "activeAcceptanceIssues": issue_ids,
        "ownerVisualAcceptance": {
            "required": bool(ux.get("ownerVisualAcceptanceRequired")),
            "acceptedSurfaces": [item.get("id") for item in surfaces if item.get("ownerVisualAccepted")],
            "pendingSurfaces": [item.get("id") for item in surfaces if not item.get("ownerVisualAccepted")],
        },
        "releaseReady": not issue_ids and all(bool(item.get("ready")) for item in surfaces),
    }

def design_state() -> dict[str, Any]:
    design = _read_json("design/sentinel-design-system.v3.json")
    ux = _read_json("design/user-visible-acceptance.v1.json")
    ref = design.get("designReference", {})
    ux_ref = ux.get("designReference", {})
    return {
        "schema": "sentinel.control-bridge.design-state.v1",
        "direction": design.get("direction"),
        "revision": design.get("revision"),
        "referenceRepository": ref.get("repository"),
        "productionPinnedSha": ref.get("sha"),
        "labPass": ux_ref.get("labPass"),
        "productionParityClaimed": bool(ux_ref.get("productionParityClaimed")),
        "nextAction": ux_ref.get("nextAction"),
    }
