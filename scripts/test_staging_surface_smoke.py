from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.staging_surface_smoke import (
    HttpResult,
    SmokeFailure,
    validate_bridge_health,
    validate_core_health,
    validate_web_health,
    validate_site_sha,
    validate_login_probe,
    validate_robots,
)


class StagingSurfaceSmokeTests(unittest.TestCase):
    def test_bridge_requires_exact_sha(self) -> None:
        result = HttpResult(200, {}, json.dumps({"status": "ok", "sourceSha": "a" * 40}).encode())
        self.assertEqual(validate_bridge_health(result, "a" * 40)["status"], "ok")
        with self.assertRaisesRegex(SmokeFailure, "BRIDGE_SHA_MISMATCH"):
            validate_bridge_health(result, "b" * 40)

    def test_core_requires_up_and_exact_version(self) -> None:
        result = HttpResult(200, {}, json.dumps({"status": "UP", "version": "1.0.0-rc2", "source_sha": "a" * 40}).encode())
        self.assertEqual(validate_core_health(result, "1.0.0-rc2", "a" * 40)["status"], "UP")
        with self.assertRaisesRegex(SmokeFailure, "CORE_VERSION_MISMATCH"):
            validate_core_health(result, "1.0.0", "a" * 40)
        with self.assertRaisesRegex(SmokeFailure, "CORE_SHA_MISMATCH"):
            validate_core_health(result, "1.0.0-rc2", "b" * 40)

    def test_web_and_site_reject_stale_builds(self) -> None:
        web = HttpResult(200, {}, json.dumps({"service": "sentinel-web", "sourceSha": "a" * 40}).encode())
        self.assertEqual(validate_web_health(web, "a" * 40)["sourceSha"], "a" * 40)
        with self.assertRaisesRegex(SmokeFailure, "WEB_SHA_MISMATCH"):
            validate_web_health(web, "b" * 40)
        site = HttpResult(200, {}, ('<html>SENTINEL<meta name="sentinel-source-sha" content="' + "a" * 40 + '"/></html>').encode())
        self.assertEqual(validate_site_sha(site, "a" * 40)["sourceSha"], "a" * 40)
        with self.assertRaisesRegex(SmokeFailure, "PUBLIC_SITE_SHA_MISMATCH"):
            validate_site_sha(site, "b" * 40)

    def test_login_probe_distinguishes_core_denial_from_proxy_failure(self) -> None:
        good = HttpResult(
            401,
            {"x-request-id": "synthetic-abc"},
            b'{"code":"INVALID_CREDENTIALS","message":"Request rejected","request_id":"synthetic-abc"}',
        )
        self.assertEqual(validate_login_probe(good)["code"], "INVALID_CREDENTIALS")
        broken = HttpResult(
            503,
            {"x-request-id": "synthetic-abc"},
            b'{"error":"SENTINEL_CORE_URL_NOT_CONFIGURED"}',
        )
        with self.assertRaisesRegex(SmokeFailure, "WEB_CORE_LOGIN_PATH_UNHEALTHY"):
            validate_login_probe(broken)

        mismatched = HttpResult(
            401,
            {"x-request-id": "synthetic-header"},
            b'{"code":"INVALID_CREDENTIALS","message":"Request rejected","request_id":"synthetic-body"}',
        )
        with self.assertRaisesRegex(SmokeFailure, "WEB_CORE_LOGIN_REQUEST_ID_MISMATCH"):
            validate_login_probe(mismatched)

    def test_robots_keeps_prerelease_site_non_indexable(self) -> None:
        result = HttpResult(200, {}, b"User-agent: *\nDisallow: /\n")
        self.assertTrue(validate_robots(result)["preReleaseDisallow"])


if __name__ == "__main__":
    unittest.main()
