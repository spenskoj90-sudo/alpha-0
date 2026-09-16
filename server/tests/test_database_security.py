import pytest

from app.core.database_security import validate_database_url


def test_remote_production_database_requires_tls():
    with pytest.raises(RuntimeError, match="requires sslmode"):
        validate_database_url("postgresql+psycopg://user:pass@db.example.test/sentinel", "production")


def test_remote_production_database_accepts_required_tls():
    validate_database_url(
        "postgresql+psycopg://user:pass@db.example.test/sentinel?sslmode=require&channel_binding=require",
        "production",
    )


def test_local_production_database_may_use_private_plaintext_transport():
    validate_database_url("postgresql+psycopg://user:pass@postgres:5432/sentinel", "production")


def test_development_does_not_impose_production_database_transport_policy():
    validate_database_url("postgresql+psycopg://user:pass@db.example.test/sentinel", "development")
