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


def test_production_requires_database_url_but_development_allows_absence():
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        validate_database_url(None, "production")
    validate_database_url(None, "development")
    validate_database_url("", "")


@pytest.mark.parametrize(
    "url",
    [
        "https://db.example.test/sentinel",
        "postgresql:///sentinel",
    ],
)
def test_production_rejects_non_postgres_or_hostless_database_urls(url):
    with pytest.raises(RuntimeError, match="must be a PostgreSQL URL"):
        validate_database_url(url, "production")


@pytest.mark.parametrize("sslmode", ["verify-ca", "verify-full"])
def test_remote_production_database_accepts_all_secure_ssl_modes(sslmode):
    validate_database_url(
        f"postgresql://user:pass@db.example.test/sentinel?sslmode={sslmode}",
        " PRODUCTION ",
    )
