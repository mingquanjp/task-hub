"""Temporary migrated database fixtures for persistence and API integration tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def database_url(tmp_path: Path) -> Generator[str, None, None]:
    """Create a fresh SQLite file and apply the real Alembic migration to it."""
    database_path = tmp_path / "taskhub.db"
    sync_url = f"sqlite:///{database_path}"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    engine = create_engine(sync_url)

    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield f"sqlite+aiosqlite:///{database_path}"
    finally:
        engine.dispose()


def migration_config() -> Config:
    """Build an Alembic configuration for migration round-trip tests."""
    return Config(str(PROJECT_ROOT / "alembic.ini"))
