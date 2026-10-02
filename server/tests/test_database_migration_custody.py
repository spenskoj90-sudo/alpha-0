import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def test_migration_prefers_its_own_custody_and_preserves_legacy_development(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'migrate.py'
    spec = importlib.util.spec_from_file_location('migration_custody_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('DATABASE_URL', 'runtime-fixture')
    monkeypatch.setenv('DATABASE_MIGRATION_URL', 'migration-fixture')
    assert module.migration_database_url() == 'migration-fixture'
    monkeypatch.delenv('DATABASE_MIGRATION_URL')
    assert module.migration_database_url() == 'runtime-fixture'


def test_serving_entrypoint_discards_migration_credential():
    environment = dict(os.environ)
    environment.pop('DATABASE_URL', None)
    environment.update(SENTINEL_ENV='development', DATABASE_MIGRATION_URL='migration-fixture',
                       SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE='false')
    result = subprocess.run([sys.executable, '-c',
        "import os; import app.entrypoint; assert 'DATABASE_MIGRATION_URL' not in os.environ"],
        env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_production_cannot_serve_without_restricted_role_guard():
    environment = dict(os.environ)
    environment.update(SENTINEL_ENV='production', SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE='false')
    result = subprocess.run([sys.executable, '-c', 'import app.entrypoint'],
                            env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Production requires SENTINEL_REQUIRE_RESTRICTED_DATABASE_ROLE=true' in result.stderr
