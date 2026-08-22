from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SENTINEL CORE"
    environment: str = "development"
    database_url: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel"
    session_ttl_seconds: int = 900
    challenge_ttl_seconds: int = 60
    max_body_bytes: int = 1_048_576
    allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_prefix="SENTINEL_", env_file=".env", extra="ignore")


settings = Settings()
