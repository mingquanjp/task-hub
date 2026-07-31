"""Tests for SQLAlchemy database primitives and label relationship mapping."""

from uuid import uuid4

import pytest
from sqlalchemy import inspect

from taskhub.core.config import Settings
from taskhub.infrastructure.database.base import Base
from taskhub.infrastructure.database.models import (
    LabelModel,
    ProjectModel,
    RefreshTokenModel,
    UserModel,
    UserRole,
)
from taskhub.infrastructure.database.session import Database


def test_database_builds_an_async_engine_and_non_expiring_session_factory() -> None:
    database = Database(
        "postgresql+psycopg://taskhub:secret@ep-example.us-east-2.aws.neon.tech/"
        "taskhub?sslmode=require"
    )

    assert database.engine.url.get_backend_name() == "postgresql"
    assert database.engine.url.get_driver_name() == "psycopg"
    assert database.session_factory.kw["expire_on_commit"] is False


@pytest.mark.asyncio
async def test_database_disposes_without_opening_a_connection() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://taskhub:secret@localhost/taskhub",
    )
    database = Database(settings.database_url)

    await database.dispose()


def test_project_and_label_models_define_the_expected_schema() -> None:
    projects = Base.metadata.tables["projects"]
    labels = Base.metadata.tables["labels"]

    assert {column.name for column in projects.columns} == {"id", "created_at"}
    assert {column.name for column in labels.columns} == {
        "id",
        "project_id",
        "name",
        "color",
        "created_at",
    }
    foreign_key = next(iter(labels.foreign_keys))
    assert foreign_key.target_fullname == "projects.id"
    assert foreign_key.ondelete == "CASCADE"
    assert labels.c.project_id.nullable is False
    assert labels.c.name.nullable is False
    assert labels.c.color.nullable is False
    assert {index.name for index in labels.indexes} == {"ix_labels_project_id"}


def test_project_and_label_models_have_a_bidirectional_relationship() -> None:
    project = ProjectModel(id=uuid4())
    label = LabelModel(id=uuid4(), project_id=project.id, name="Backend", color="#1A73E8")

    project.labels.append(label)

    assert label.project is project
    project_labels = inspect(ProjectModel).relationships["labels"]
    assert project_labels.uselist is True
    assert project_labels.passive_deletes is True
    assert "delete-orphan" in project_labels.cascade
    assert inspect(LabelModel).relationships["project"].uselist is False


def test_user_and_refresh_token_models_define_security_schema() -> None:
    users = Base.metadata.tables["users"]
    refresh_tokens = Base.metadata.tables["refresh_tokens"]

    assert {column.name for column in users.columns} == {
        "id",
        "email",
        "full_name",
        "hashed_password",
        "role",
        "is_active",
        "created_at",
    }
    assert users.c.email.nullable is False
    assert users.c.hashed_password.nullable is False
    assert users.c.email.unique is True
    assert "ck_users_role_valid" in {constraint.name for constraint in users.constraints}
    assert {column.name for column in refresh_tokens.columns} == {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "revoked_at",
        "created_at",
    }
    foreign_key = next(iter(refresh_tokens.foreign_keys))
    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"
    assert refresh_tokens.c.token_hash.unique is True
    assert UserModel(role=UserRole.MEMBER).role == UserRole.MEMBER


def test_user_and_refresh_token_relationship_cascades() -> None:
    user = UserModel(email="user@example.com", full_name="User", hashed_password="hash")
    token = RefreshTokenModel(user=user, token_hash="a" * 64)

    assert token.user is user
    assert user.refresh_tokens == [token]
    assert inspect(UserModel).relationships["refresh_tokens"].passive_deletes is True
    assert "delete-orphan" in inspect(UserModel).relationships["refresh_tokens"].cascade
