"""Tests for environment-backed configuration."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from taskhub.core.config import SecuritySettings, Settings


def test_settings_normalizes_a_neon_connection_url() -> None:
    settings = Settings(
        database_url=(
            "postgresql://taskhub:secret@ep-example.us-east-2.aws.neon.tech/taskhub?sslmode=require"
        ),
    )

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_rejects_a_non_postgresql_database_url() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(database_url="mysql://localhost/taskhub")


def test_settings_fails_fast_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError, match="database_url"):
        Settings()  # type: ignore[call-arg]  # Loaded from environment at runtime.


def test_security_settings_validate_secret_and_token_policy() -> None:
    settings = SecuritySettings(
        jwt_secret_key=SecretStr("x" * 32),
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
    )

    assert settings.jwt_secret_key.get_secret_value() == "x" * 32
    assert settings.jwt_algorithm == "HS256"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("jwt_secret_key", SecretStr("too-short"), "32 characters"),
        ("jwt_algorithm", "RS256", "HS256"),
        ("jwt_access_token_expire_minutes", 0, "greater than 0"),
        ("jwt_refresh_token_expire_days", 0, "greater than 0"),
    ],
)
def test_security_settings_reject_unsafe_token_configuration(
    field: str,
    value: object,
    message: str,
) -> None:
    values: dict[str, object] = {"jwt_secret_key": SecretStr("x" * 32), field: value}
    with pytest.raises(ValidationError, match=message):
        SecuritySettings(**values)
