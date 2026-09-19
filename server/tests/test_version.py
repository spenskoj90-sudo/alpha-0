from pathlib import Path

import app.version as version_module


def test_source_version_uses_canonical_version_file(tmp_path: Path) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3-rc4\n", encoding="utf-8")
    assert version_module.resolve_app_version(version_file) == "1.2.3-rc4"


def test_installed_wheel_falls_back_to_distribution_metadata(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing-version"
    monkeypatch.setattr(version_module, "distribution_version", lambda _: "1.2.3rc4")
    assert version_module.resolve_app_version(missing) == "1.2.3-rc4"
