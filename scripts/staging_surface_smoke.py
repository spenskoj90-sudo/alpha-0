#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_BRIDGE_URL = "https://sentinel-control-bridge-staging.onrender.com"
_CORE_URL = "https://sentinel-core-staging.onrender.com"
_WEB_URL = "https://sentinel-web-staging-fxhn.onrender.com"
_SITE_URL = "https://sentinel-public-site-staging.onrender.com"


class SmokeFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> dict[str, Any]:
        try:
            value = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SmokeFailure(f"NON_JSON_RESPONSE:{self.status}") from exc
        if not isinstance(value, dict):
            raise SmokeFailure(f"NON_OBJECT_JSON_RESPONSE:{self.status}")
        return value


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 15.0,
) -> HttpResult:
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"User-Agent": "sentinel-staging-synthetic/1", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return HttpResult(
                int(getattr(response, "status", 0)),
                {key.lower(): value for key, value in response.headers.items()},
                response.read(262_145),
            )
    except urllib.error.HTTPError as exc:
        return HttpResult(
            int(exc.code),
            {key.lower(): value for key, value in exc.headers.items()},
            exc.read(262_145),
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SmokeFailure(f"NETWORK_ERROR:{type(exc).__name__}") from exc


def _base(url: str) -> str:
    return url.rstrip("/")


def validate_bridge_health(result: HttpResult, expected_sha: str) -> dict[str, Any]:
    if result.status != 200:
        raise SmokeFailure(f"BRIDGE_HEALTH_HTTP_{result.status}")
    payload = result.json()
    if payload.get("status") != "ok":
        raise SmokeFailure("BRIDGE_HEALTH_NOT_OK")
    if payload.get("sourceSha") != expected_sha:
        raise SmokeFailure(f"BRIDGE_SHA_MISMATCH:{payload.get('sourceSha')}")
    return payload


def validate_core_health(result: HttpResult, expected_version: str) -> dict[str, Any]:
    if result.status != 200:
        raise SmokeFailure(f"CORE_HEALTH_HTTP_{result.status}")
    payload = result.json()
    if payload.get("status") != "UP":
        raise SmokeFailure("CORE_HEALTH_NOT_UP")
    if payload.get("version") != expected_version:
        raise SmokeFailure(f"CORE_VERSION_MISMATCH:{payload.get('version')}")
    return payload


def validate_login_probe(result: HttpResult) -> dict[str, Any]:
    if result.status != 401:
        try:
            payload = result.json()
        except SmokeFailure:
            payload = {}
        error = payload.get("error") or payload.get("detail") or "unknown"
        raise SmokeFailure(f"WEB_CORE_LOGIN_PATH_UNHEALTHY:{result.status}:{error}")
    payload = result.json()
    if payload.get("detail") != "INVALID_CREDENTIALS":
        raise SmokeFailure(f"WEB_CORE_LOGIN_UNEXPECTED_BODY:{payload}")
    request_id = result.headers.get("x-request-id", "")
    if not _REQUEST_ID.fullmatch(request_id):
        raise SmokeFailure("WEB_CORE_LOGIN_REQUEST_ID_MISSING")
    return {"status": result.status, "detail": payload["detail"], "requestIdPresent": True}


def validate_html(result: HttpResult, label: str) -> dict[str, Any]:
    if result.status != 200:
        raise SmokeFailure(f"{label}_HTTP_{result.status}")
    text = result.body.decode("utf-8", errors="replace")
    if "SENTINEL" not in text.upper():
        raise SmokeFailure(f"{label}_BRAND_MARKER_MISSING")
    return {"status": result.status, "brandMarker": True}


def validate_robots(result: HttpResult) -> dict[str, Any]:
    if result.status != 200:
        raise SmokeFailure(f"PUBLIC_ROBOTS_HTTP_{result.status}")
    text = result.body.decode("utf-8", errors="replace")
    if "Disallow: /" not in text:
        raise SmokeFailure("PUBLIC_ROBOTS_PRERELEASE_GUARD_MISSING")
    return {"status": result.status, "preReleaseDisallow": True}


def wait_for_exact_bridge(
    bridge_url: str,
    expected_sha: str,
    *,
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = "not-probed"
    while time.monotonic() < deadline:
        try:
            result = _request("GET", f"{_base(bridge_url)}/healthz")
            payload = result.json() if result.status == 200 else {}
            last = f"http={result.status},sha={payload.get('sourceSha')}"
            if result.status == 200 and payload.get("status") == "ok" and payload.get("sourceSha") == expected_sha:
                return validate_bridge_health(result, expected_sha)
        except SmokeFailure as exc:
            last = str(exc)
        time.sleep(poll_seconds)
    raise SmokeFailure(f"BRIDGE_EXACT_SHA_TIMEOUT:{last}")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not _SHA40.fullmatch(args.expected_sha):
        raise SmokeFailure("EXPECTED_SHA_INVALID")
    if not args.expected_version.strip():
        raise SmokeFailure("EXPECTED_VERSION_MISSING")

    evidence: dict[str, Any] = {
        "schema": "sentinel.staging-synthetic.v1",
        "expectedSourceSha": args.expected_sha,
        "expectedVersion": args.expected_version,
        "observedAt": datetime.now(UTC).isoformat(),
        "surfaces": {},
    }

    evidence["surfaces"]["bridge"] = wait_for_exact_bridge(
        _BRIDGE_URL,
        args.expected_sha,
        timeout_seconds=args.deploy_timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    evidence["surfaces"]["core"] = validate_core_health(
        _request("GET", f"{_CORE_URL}/healthz"),
        args.expected_version,
    )
    evidence["surfaces"]["web"] = validate_html(
        _request("GET", _WEB_URL),
        "WEB_ROOT",
    )

    probe_id = re.sub(r"[^A-Za-z0-9_-]", "-", args.probe_id)[:48] or "probe"
    body = json.dumps(
        {
            "email": f"synthetic-{args.expected_sha[:12]}-{probe_id}@example.invalid",
            "password": "SENTINEL-Synthetic-Never-Valid-2026!",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    login = _request(
        "POST",
        f"{_WEB_URL}/api/session/login",
        body=body,
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "origin": _WEB_URL,
            "x-request-id": f"synthetic-{args.expected_sha[:12]}-{probe_id}"[:128],
        },
    )
    evidence["surfaces"]["webCoreLogin"] = validate_login_probe(login)

    evidence["surfaces"]["publicSite"] = validate_html(
        _request("GET", _SITE_URL),
        "PUBLIC_SITE_ROOT",
    )
    evidence["surfaces"]["publicRobots"] = validate_robots(
        _request("GET", f"{_SITE_URL}/robots.txt")
    )
    evidence["result"] = "PASS"
    return evidence


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--expected-sha", required=True)
    value.add_argument("--expected-version", required=True)
    value.add_argument("--probe-id", default=os.getenv("GITHUB_RUN_ID", "manual"))
    value.add_argument("--deploy-timeout-seconds", type=int, default=900)
    value.add_argument("--poll-seconds", type=int, default=15)
    value.add_argument("--output", required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        evidence = run(args)
    except Exception as exc:
        evidence = {
            "schema": "sentinel.staging-synthetic.v1",
            "expectedSourceSha": args.expected_sha,
            "expectedVersion": args.expected_version,
            "observedAt": datetime.now(UTC).isoformat(),
            "result": "FAIL",
            "error": f"{type(exc).__name__}:{exc}",
        }
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(evidence, sort_keys=True), file=sys.stderr)
        return 1
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
