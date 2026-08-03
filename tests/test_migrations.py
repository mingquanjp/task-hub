"""Tests that the initial Alembic revision can be upgraded and downgraded."""

from alembic import command
from sqlalchemy import create_engine, inspect

from tests.conftest import migration_config


def test_initial_migration_creates_and_removes_schema(database_url: str) -> None:
    """Run downgrade then upgrade against the temporary migrated database."""
    sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    engine = create_engine(sync_url)
    config = migration_config()

    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "-1")
            assert {"users", "refresh_tokens"}.issubset(inspect(connection).get_table_names())

            command.upgrade(config, "head")
            command.downgrade(config, "c7a8d4a9ea90")
            assert set(inspect(connection).get_table_names()) == {
                "alembic_version",
                "labels",
                "projects",
            }

            command.upgrade(config, "head")
            inspector = inspect(connection)
            assert {
                "alembic_version",
                "labels",
                "projects",
                "refresh_tokens",
                "users",
                "workspaces",
                "workspace_members",
            } == set(inspector.get_table_names())
            assert {index["name"] for index in inspector.get_indexes("labels")} == {
                "ix_labels_project_id"
            }
            foreign_keys = inspector.get_foreign_keys("labels")
            assert foreign_keys[0]["referred_table"] == "projects"
            refresh_foreign_keys = inspector.get_foreign_keys("refresh_tokens")
            assert refresh_foreign_keys[0]["referred_table"] == "users"
            assert {index["name"] for index in inspector.get_indexes("users")} == {"ix_users_email"}
            assert {index["name"] for index in inspector.get_indexes("refresh_tokens")} == {
                "ix_refresh_tokens_user_id"
            }
    finally:
        engine.dispose()
