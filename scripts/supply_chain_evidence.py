#!/usr/bin/env python3
"""Build and verify exact-SHA software supply-chain evidence for SENTINEL.

The evidence is intentionally descriptive. It inventories resolved dependencies and
binds generated CycloneDX documents to one repository SHA. It does not sign release
artifacts, publish a release, deploy production, or claim external-environment acceptance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCHEMA = "sentinel.supply-chain-evidence.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GRADLE_COORD_RE = re.compile(r"([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+):([^\s]+)")


def canonical_digest(document: dict[str, Any]) -> str:
    payload = copy.deepcopy(document)
    payload.pop("evidenceDigest", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _component(*, ecosystem: str, name: str, version: str, purl: str, scope: str = "required") -> dict[str, Any]:
    if not name or not version:
        raise ValueError(f"invalid {ecosystem} component")
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": purl,
        "scope": scope,
        "properties": [{"name": "sentinel:ecosystem", "value": ecosystem}],
    }


def python_components(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Python runtime inventory must be a list")
    components = []
    seen: set[tuple[str, str]] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Python runtime inventory entry must be an object")
        name = str(item.get("name", "")).strip()
        version = str(item.get("version", "")).strip()
        key = (name.lower(), version)
        if not name or not version or key in seen:
            if key in seen:
                continue
            raise ValueError("Python runtime inventory contains an invalid component")
        seen.add(key)
        components.append(
            _component(
                ecosystem="python-runtime",
                name=name,
                version=version,
                purl=f"pkg:pypi/{quote(name.lower(), safe='._-')}@{quote(version, safe='._+-')}",
            )
        )
    if not components:
        raise ValueError("Python runtime inventory is empty")
    return sorted(components, key=lambda item: (item["name"].lower(), item["version"]))


def _npm_name(package_key: str) -> str:
    marker = "node_modules/"
    if marker not in package_key:
        return ""
    return package_key.rsplit(marker, 1)[1].strip("/")


def _npm_purl(name: str, version: str) -> str:
    if name.startswith("@") and "/" in name:
        namespace, package = name.split("/", 1)
        return f"pkg:npm/{quote(namespace, safe='')}/{quote(package, safe='._-')}@{quote(version, safe='._+-')}"
    return f"pkg:npm/{quote(name, safe='._-')}@{quote(version, safe='._+-')}"


def web_components(path: Path) -> list[dict[str, Any]]:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if int(lock.get("lockfileVersion", 0)) < 3:
        raise ValueError("Web lockfile must use lockfileVersion >= 3")
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("Web lockfile packages map missing")
    components = []
    seen: set[tuple[str, str, str]] = set()
    for package_key, item in packages.items():
        if not isinstance(item, dict):
            continue
        name = _npm_name(str(package_key))
        if not name:
            continue
        version = str(item.get("version", "")).strip()
        if not version:
            raise ValueError(f"Web lockfile component {name!r} lacks an exact version")
        scope = "excluded" if item.get("dev") is True else "required"
        key = (name, version, scope)
        if key in seen:
            continue
        seen.add(key)
        component = _component(
            ecosystem="web-lockfile",
            name=name,
            version=version,
            purl=_npm_purl(name, version),
            scope=scope,
        )
        integrity = item.get("integrity")
        if isinstance(integrity, str) and integrity:
            component["properties"].append({"name": "sentinel:npm-integrity", "value": integrity})
        components.append(component)
    if not components:
        raise ValueError("Web lockfile inventory is empty")
    return sorted(components, key=lambda item: (item["name"], item["version"], item["scope"]))


def android_components(path: Path) -> list[dict[str, Any]]:
    components = []
    seen: set[tuple[str, str, str]] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = GRADLE_COORD_RE.search(line)
        if not match:
            continue
        group, artifact, declared_version = match.groups()
        version = declared_version.rstrip("(*)")
        arrow = re.search(r"\s+->\s+([^\s]+)", line)
        if arrow:
            version = arrow.group(1).rstrip("(*)")
        if version.startswith("{") or version in {"FAILED", "project"}:
            continue
        key = (group, artifact, version)
        if key in seen:
            continue
        seen.add(key)
        components.append(
            _component(
                ecosystem="android-debug-runtime",
                name=f"{group}:{artifact}",
                version=version,
                purl=f"pkg:maven/{quote(group, safe='._-')}/{quote(artifact, safe='._-')}@{quote(version, safe='._+-')}",
            )
        )
    if not components:
        raise ValueError("Android resolved dependency inventory is empty")
    return sorted(components, key=lambda item: (item["name"], item["version"]))


def launcher_components(path: Path) -> list[dict[str, Any]]:
    package = json.loads(path.read_text(encoding="utf-8"))
    dependencies = package.get("dependencies")
    packaging = package.get("sentinelPackaging")
    if not isinstance(dependencies, dict) or not isinstance(packaging, dict):
        raise ValueError("Launcher package metadata is incomplete")
    electron_version = str(dependencies.get("electron", "")).strip()
    if not electron_version or electron_version != str(packaging.get("electronVersion", "")).strip():
        raise ValueError("Launcher Electron dependency/version pin mismatch")
    runtime_sha = str(packaging.get("electronWin32X64Sha256", "")).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", runtime_sha):
        raise ValueError("Launcher Electron runtime SHA-256 is invalid")
    component = _component(
        ecosystem="packaged-companion",
        name="electron",
        version=electron_version,
        purl=f"pkg:npm/electron@{quote(electron_version, safe='._+-')}",
    )
    component["hashes"] = [{"alg": "SHA-256", "content": runtime_sha}]
    component["properties"].append({"name": "sentinel:asset", "value": f"electron-v{electron_version}-win32-x64.zip"})
    return [component]


def validate_container_sbom(path: Path) -> tuple[dict[str, Any], int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("bomFormat") != "CycloneDX":
        raise ValueError("Container SBOM is not CycloneDX")
    spec_version = str(payload.get("specVersion", ""))
    if not re.fullmatch(r"1\.[4-9]", spec_version):
        raise ValueError("Container SBOM uses an unsupported CycloneDX specVersion")
    components = payload.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("Container SBOM components are empty")
    return payload, len(components)


def application_sbom(repository: str, sha: str, version: str, components: list[dict[str, Any]]) -> dict[str, Any]:
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for component in components:
        properties = component.get("properties") or []
        ecosystem = next((p.get("value") for p in properties if p.get("name") == "sentinel:ecosystem"), "unknown")
        key = (str(ecosystem), component["name"], component["version"], component.get("scope", "required"))
        unique[key] = component
    ordered = [unique[key] for key in sorted(unique)]
    if not ordered:
        raise ValueError("Application SBOM would be empty")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "sentinel-platform",
                "version": version,
                "properties": [
                    {"name": "sentinel:repository", "value": repository},
                    {"name": "sentinel:source-sha", "value": sha},
                    {"name": "sentinel:evidence-scope", "value": "resolved-build-and-runtime-dependencies"},
                ],
            }
        },
        "components": ordered,
    }


def _count_ecosystems(components: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for component in components:
        ecosystem = next(
            (str(item.get("value")) for item in component.get("properties", []) if item.get("name") == "sentinel:ecosystem"),
            "unknown",
        )
        counts[ecosystem] = counts.get(ecosystem, 0) + 1
    return dict(sorted(counts.items()))


def build_evidence(
    *,
    repository: str,
    sha: str,
    version: str,
    python_runtime: Path,
    web_lock: Path,
    gradle_deps: Path,
    launcher_package: Path,
    container_sbom: Path,
    container_image_id: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if not REPO_RE.fullmatch(repository):
        raise ValueError("repository must be owner/name")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("sha must be 40 lowercase hexadecimal characters")
    if not version.strip():
        raise ValueError("version is empty")
    inputs = [python_runtime, web_lock, gradle_deps, launcher_package, container_sbom, container_image_id]
    for path in inputs:
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"required supply-chain input is missing or empty: {path}")

    python_items = python_components(python_runtime)
    web_items = web_components(web_lock)
    android_items = android_components(gradle_deps)
    launcher_items = launcher_components(launcher_package)
    app_bom = application_sbom(repository, sha, version.strip(), python_items + web_items + android_items + launcher_items)
    _, container_count = validate_container_sbom(container_sbom)

    image_id = container_image_id.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("container image ID must be a sha256 digest")

    output_dir.mkdir(parents=True, exist_ok=True)
    app_path = output_dir / "sentinel-application.cdx.json"
    app_path.write_text(json.dumps(app_bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    container_out = output_dir / "sentinel-core-container.cdx.json"
    if container_sbom.resolve() != container_out.resolve():
        container_out.write_bytes(container_sbom.read_bytes())

    input_evidence = []
    for name, path in (
        ("pythonRuntime", python_runtime),
        ("webLockfile", web_lock),
        ("androidDebugRuntime", gradle_deps),
        ("launcherPackage", launcher_package),
    ):
        input_evidence.append({"name": name, "sha256": file_digest(path), "sizeBytes": path.stat().st_size})

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source": {"repository": repository, "sha": sha, "version": version.strip()},
        "claims": {
            "signedReleaseArtifact": False,
            "releasePublished": False,
            "productionDeployed": False,
            "externalEnvironmentAcceptanceSatisfied": False,
            "cryptographicAttestationProduced": False,
        },
        "container": {
            "imageId": image_id,
            "sbom": {
                "path": container_out.name,
                "digest": file_digest(container_out),
                "componentCount": container_count,
                "format": "CycloneDX",
            },
        },
        "application": {
            "sbom": {
                "path": app_path.name,
                "digest": file_digest(app_path),
                "componentCount": len(app_bom["components"]),
                "ecosystems": _count_ecosystems(app_bom["components"]),
                "format": "CycloneDX",
            }
        },
        "inputs": input_evidence,
    }
    manifest["evidenceDigest"] = canonical_digest(manifest)
    manifest_path = output_dir / "supply-chain-evidence.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_evidence(
    input_dir: Path,
    *,
    expected_repository: str | None = None,
    expected_sha: str | None = None,
    expected_version: str | None = None,
) -> dict[str, Any]:
    manifest_path = input_dir / "supply-chain-evidence.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("status") != "PASS":
        raise ValueError("invalid supply-chain schema or non-PASS status")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("missing supply-chain source")
    repository = source.get("repository")
    sha = source.get("sha")
    version = source.get("version")
    if not isinstance(repository, str) or not REPO_RE.fullmatch(repository):
        raise ValueError("invalid source repository")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("invalid source SHA")
    if not isinstance(version, str) or not version:
        raise ValueError("invalid source version")
    if expected_repository is not None and repository != expected_repository:
        raise ValueError("repository mismatch")
    if expected_sha is not None and sha != expected_sha:
        raise ValueError("source SHA mismatch")
    if expected_version is not None and version != expected_version:
        raise ValueError("version mismatch")

    expected_claims = {
        "signedReleaseArtifact": False,
        "releasePublished": False,
        "productionDeployed": False,
        "externalEnvironmentAcceptanceSatisfied": False,
        "cryptographicAttestationProduced": False,
    }
    if manifest.get("claims") != expected_claims:
        raise ValueError("supply-chain evidence must not overclaim release or attestation state")

    application = manifest.get("application", {}).get("sbom", {})
    container = manifest.get("container", {})
    container_sbom = container.get("sbom", {})
    image_id = container.get("imageId")
    if not isinstance(image_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("invalid container image ID")

    for label, item in (("application", application), ("container", container_sbom)):
        if item.get("format") != "CycloneDX" or int(item.get("componentCount", 0)) <= 0:
            raise ValueError(f"invalid {label} SBOM evidence")
        path_value = item.get("path")
        digest = item.get("digest")
        if not isinstance(path_value, str) or Path(path_value).name != path_value:
            raise ValueError(f"invalid {label} SBOM path")
        path = input_dir / path_value
        if not path.is_file() or path.stat().st_size <= 0:
            raise ValueError(f"missing {label} SBOM")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest) or file_digest(path) != digest:
            raise ValueError(f"{label} SBOM digest mismatch")

    app_payload = json.loads((input_dir / application["path"]).read_text(encoding="utf-8"))
    if app_payload.get("bomFormat") != "CycloneDX" or app_payload.get("specVersion") != "1.6":
        raise ValueError("application SBOM format mismatch")
    app_components = app_payload.get("components")
    if not isinstance(app_components, list) or len(app_components) != int(application["componentCount"]):
        raise ValueError("application SBOM component count mismatch")
    properties = app_payload.get("metadata", {}).get("component", {}).get("properties", [])
    property_map = {item.get("name"): item.get("value") for item in properties if isinstance(item, dict)}
    if property_map.get("sentinel:repository") != repository or property_map.get("sentinel:source-sha") != sha:
        raise ValueError("application SBOM source binding mismatch")

    _, actual_container_count = validate_container_sbom(input_dir / container_sbom["path"])
    if actual_container_count != int(container_sbom["componentCount"]):
        raise ValueError("container SBOM component count mismatch")

    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or {item.get("name") for item in inputs if isinstance(item, dict)} != {
        "pythonRuntime", "webLockfile", "androidDebugRuntime", "launcherPackage"
    }:
        raise ValueError("input evidence set mismatch")
    for item in inputs:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("sha256"), str)
            or not DIGEST_RE.fullmatch(item["sha256"])
            or int(item.get("sizeBytes", 0)) <= 0
        ):
            raise ValueError("invalid input evidence")

    digest = manifest.get("evidenceDigest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest) or digest != canonical_digest(manifest):
        raise ValueError("supply-chain evidence digest mismatch")
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--repository", required=True)
    build.add_argument("--sha", required=True)
    build.add_argument("--version", required=True)
    build.add_argument("--python-runtime", required=True)
    build.add_argument("--web-lock", required=True)
    build.add_argument("--gradle-deps", required=True)
    build.add_argument("--launcher-package", required=True)
    build.add_argument("--container-sbom", required=True)
    build.add_argument("--container-image-id", required=True)
    build.add_argument("--output-dir", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--input-dir", required=True)
    verify.add_argument("--expected-repository")
    verify.add_argument("--expected-sha")
    verify.add_argument("--expected-version")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "build":
            manifest = build_evidence(
                repository=args.repository,
                sha=args.sha,
                version=args.version,
                python_runtime=Path(args.python_runtime),
                web_lock=Path(args.web_lock),
                gradle_deps=Path(args.gradle_deps),
                launcher_package=Path(args.launcher_package),
                container_sbom=Path(args.container_sbom),
                container_image_id=Path(args.container_image_id),
                output_dir=Path(args.output_dir),
            )
            print(f"supply-chain evidence PASS: {manifest['evidenceDigest']}")
        else:
            manifest = verify_evidence(
                Path(args.input_dir),
                expected_repository=args.expected_repository,
                expected_sha=args.expected_sha,
                expected_version=args.expected_version,
            )
            print(f"supply-chain evidence verified: {manifest['evidenceDigest']}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"supply-chain evidence FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
