"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings required by TaskHub infrastructure."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    redis_url: str | None = None
    task_list_cache_ttl_seconds: int = 300
    email_enabled: bool = False

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        """Ensure APP_ENV is one of the allowed values."""
        allowed = {"development", "test", "production"}
        if value not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return value

    @field_validator("task_list_cache_ttl_seconds")
    @classmethod
    def validate_ttl(cls, value: int) -> int:
        """Ensure TTL is greater than 0."""
        if value <= 0:
            raise ValueError("TASK_LIST_CACHE_TTL_SECONDS must be greater than 0")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Normalize a Neon PostgreSQL URL for SQLAlchemy's async psycopg driver."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use a PostgreSQL connection scheme")
        return value


class SecuritySettings(BaseSettings):
    """Validated settings for password hashing and future JWT token issuance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "taskhub"
    jwt_audience: str = "taskhub-api"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        """Require enough entropy for the symmetric signing secret."""
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        """Keep the initial implementation on the explicitly supported algorithm."""
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        return value

    @field_validator("jwt_access_token_expire_minutes")
    @classmethod
    def validate_access_expiry(cls, value: int) -> int:
        """Reject non-positive access-token lifetimes."""
        if value <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        return value

    @field_validator("jwt_refresh_token_expire_days")
    @classmethod
    def validate_refresh_expiry(cls, value: int) -> int:
        """Reject non-positive refresh-token lifetimes."""
        if value <= 0:
            raise ValueError("JWT_REFRESH_TOKEN_EXPIRE_DAYS must be greater than 0")
        return value


@lru_cache
def get_settings() -> Settings:
    """Load and cache validated application settings."""
    return Settings()  # type: ignore[call-arg]  # Loaded from environment at runtime.


@lru_cache
def get_security_settings() -> SecuritySettings:
    """Load and cache validated security settings at the auth composition boundary."""
    return SecuritySettings()  # type: ignore[call-arg]  # Loaded from environment at runtime.
