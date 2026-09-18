#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PlatformBaselineTests(unittest.TestCase):
    def test_android_toolchain_frontier_is_locked(self) -> None:
        root = read("build.gradle.kts")
        wrapper = read("gradle/wrapper/gradle-wrapper.properties")
        app = read("app/build.gradle.kts")

        self.assertIn('com.android.application") version "9.3.1"', root)
        self.assertIn("kotlin-gradle-plugin:2.4.20", root)
        self.assertIn('org.jetbrains.kotlin.plugin.compose") version "2.4.20"', root)
        self.assertNotIn("org.jetbrains.kotlin.android", root)
        self.assertIn("gradle-9.7.0-bin.zip", wrapper)
        self.assertIn(
            "distributionSha256Sum=84fbba45c7f4c64abc77460e1c00f541e9f960e3c7ed2538f1ede19eacd873ae",
            wrapper,
        )
        self.assertIn("compileSdk = 37", app)
        self.assertIn("targetSdk = 36", app)
        self.assertIn("sourceCompatibility = JavaVersion.VERSION_17", app)
        self.assertIn("targetCompatibility = JavaVersion.VERSION_17", app)
        self.assertIn("googleid:googleid:1.2.1", app)
        version = re.search(r"versionCode\s*=\s*(\d+)", app)
        self.assertIsNotNone(version)
        self.assertGreaterEqual(int(version.group(1)), 10007)

    def test_core_runtime_is_python_314(self) -> None:
        pyproject = read("server/pyproject.toml")
        dockerfile = read("server/Dockerfile")
        self.assertIn('requires-python = ">=3.14,<3.15"', pyproject)
        self.assertIn("fastapi>=0.141.1,<1.0", pyproject)
        self.assertIn("pydantic>=2.13.5,<3.0", pyproject)
        self.assertIn("psycopg[binary]>=3.3.6,<4.0", pyproject)
        self.assertIn("python:3.14.7-slim@sha256:", dockerfile)

    def test_web_runtime_is_node_24_lts(self) -> None:
        package = json.loads(read("web/package.json"))
        lock = json.loads(read("web/package-lock.json"))
        dockerfile = read("web/Dockerfile")

        self.assertEqual(package["engines"]["node"], "24.x")
        self.assertEqual(package["dependencies"]["next"], "16.3.5")
        self.assertEqual(package["dependencies"]["react"], "19.3.0")
        self.assertEqual(package["devDependencies"]["typescript"], "6.0.3")
        self.assertEqual(package["devDependencies"]["eslint"], "10.10.0")
        self.assertEqual(package["devDependencies"]["vitest"], "5.0.0")
        self.assertEqual(lock["packages"][""]["engines"]["node"], "24.x")
        self.assertEqual(lock["packages"][""]["dependencies"], package["dependencies"])
        self.assertEqual(lock["packages"][""]["devDependencies"], package["devDependencies"])
        self.assertIn("node:24.21.0-alpine3.24@sha256:", dockerfile)

    def test_companion_runtime_is_current_stable_electron(self) -> None:
        package = json.loads(read("launcher/package.json"))
        self.assertEqual(package["engines"]["node"], ">=24")
        self.assertEqual(package["dependencies"]["electron"], "44.4.2")
        self.assertEqual(package["sentinelPackaging"]["electronVersion"], "44.4.2")
        self.assertEqual(
            package["sentinelPackaging"]["electronWin32X64Sha256"],
            "6aae435b6cd5c0eedf9fd38824bae4045ffdaecd029f0b8c8328bac3f5b71f03",
        )

    def test_reference_database_is_postgresql_18(self) -> None:
        compose = read("docker-compose.yml")
        build = read(".github/workflows/build.yml")
        self.assertIn("postgres:18.6-alpine3.24@sha256:", compose)
        self.assertIn("postgres_data:/var/lib/postgresql", compose)
        self.assertNotIn("postgres_data:/var/lib/postgresql/data", compose)
        self.assertIn("postgres:18.6-alpine3.24@sha256:", build)

    def test_ci_runs_modern_runtimes(self) -> None:
        combined = "\n".join(
            read(path)
            for path in (
                ".github/workflows/build.yml",
                ".github/workflows/android-build.yml",
                ".github/workflows/physical-test-apk.yml",
                ".github/workflows/security.yml",
                ".github/workflows/p1-evidence.yml",
                ".github/workflows/packaged-companion.yml",
                ".github/workflows/supply-chain-evidence.yml",
            )
        )
        self.assertNotIn('java-version: "17"', combined)
        self.assertNotIn('node-version: "22"', combined)
        self.assertNotIn('python-version: "3.12"', combined)
        self.assertIn('java-version: "25"', combined)
        self.assertIn('node-version: "24"', combined)
        self.assertIn('python-version: "3.14"', combined)
        self.assertIn("api-level: 36", read(".github/workflows/build.yml"))

    def test_dependency_freshness_is_continuous(self) -> None:
        dependabot = read(".github/dependabot.yml")
        for ecosystem in ("gradle", "pip", "npm", "docker", "github-actions"):
            self.assertIn(f"package-ecosystem: {ecosystem}", dependabot)


if __name__ == "__main__":
    unittest.main()
