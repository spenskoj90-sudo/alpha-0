from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path

_PACKAGE_NAME = "sentinel-core"
_RC_SUFFIX = re.compile(r"(?<=\d)rc(?=\d+$)")


def normalize_version(value: str) -> str:
    """Return the repository's canonical display form for a PEP 440 version."""
    return _RC_SUFFIX.sub("-rc", value.strip().lower())


def resolve_app_version(version_file: Path | None = None) -> str:
    """Resolve the canonical application version in source and installed-wheel layouts."""
    candidate = version_file or (Path(__file__).resolve().parents[2] / "VERSION")
    if candidate.is_file():
        value = candidate.read_text(encoding="utf-8").strip()
        if value:
            return value
    try:
        return normalize_version(distribution_version(_PACKAGE_NAME))
    except PackageNotFoundError as exc:
        raise RuntimeError("SENTINEL application version is unavailable") from exc


APP_VERSION = resolve_app_version()
