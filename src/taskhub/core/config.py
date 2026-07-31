"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings required by TaskHub infrastructure."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Normalize a Neon PostgreSQL URL for SQLAlchemy's async psycopg driver."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use a PostgreSQL connection scheme")
        return value


@lru_cache
def get_settings() -> Settings:
    """Load and cache validated application settings."""
    return Settings()  # type: ignore[call-arg]  # Loaded from environment at runtime.
