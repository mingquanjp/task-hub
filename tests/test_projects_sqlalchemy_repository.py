"""Tests for the SQLAlchemy project repository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from taskhub.infrastructure.database.models import UserModel, WorkspaceModel
from taskhub.infrastructure.database.session import Database
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.projects.sqlalchemy_repository import SQLAlchemyProjectRepository


async def setup_workspace(database: Database) -> tuple[UUID, UUID]:
    """Create a user and workspace, returning their IDs."""
    user_id = uuid4()
    workspace_id = uuid4()
    async with database.session_factory() as session:
        session.add(
            UserModel(
                id=user_id, email=f"{user_id}@test.com", hashed_password="hash", full_name="Test"
            )
        )
        session.add(WorkspaceModel(id=workspace_id, name="Test WS", owner_id=user_id))
        await session.commit()
    return user_id, workspace_id


@pytest.mark.asyncio
async def test_repository_crud(database_url: str) -> None:
    database = Database(database_url)
    user_id, workspace_id = await setup_workspace(database)

    project = Project(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Test",
        description="Desc",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )

    # Create
    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        created = await repo.create(project)
        assert created.id == project.id
        await session.commit()

    # Get
    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        fetched = await repo.get_by_id(project.id)
        assert fetched is not None
        assert fetched.name == "Test"

    # List
    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        projects = await repo.list_by_workspace(workspace_id)
        assert len(projects) == 1
        assert projects[0].id == project.id

    # Update
    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        project.name = "New Name"
        await repo.update(project)
        await session.commit()

    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        fetched = await repo.get_by_id(project.id)
        assert fetched is not None
        assert fetched.name == "New Name"

    # Delete
    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        deleted = await repo.delete(project.id)
        assert deleted is True
        await session.commit()

    async with database.session_factory() as session:
        repo = SQLAlchemyProjectRepository(session)
        assert await repo.get_by_id(project.id) is None
