"""Tests for environment-backed configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from taskhub.core.config import Settings


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
