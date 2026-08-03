"""Database-backed tests for the Label SQLAlchemy repository."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from taskhub.infrastructure.database.models import (
    LabelModel,
    ProjectModel,
    UserModel,
    WorkspaceModel,
)
from taskhub.infrastructure.database.session import Database
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.sqlalchemy_repository import SQLAlchemyLabelRepository


async def create_project(database: Database, project_id: UUID) -> None:
    """Persist a minimal ProjectModel parent for a label test."""
    workspace_id = uuid4()
    owner_id = uuid4()
    async with database.session_factory() as session:
        session.add(UserModel(id=owner_id, email=f"{owner_id}@test.com", hashed_password="hash", full_name="Test"))
        session.add(WorkspaceModel(id=workspace_id, name="Test WS", owner_id=owner_id))
        session.add(ProjectModel(id=project_id, workspace_id=workspace_id, name="Test Project", status="ACTIVE"))
        await session.commit()


@pytest.mark.asyncio
async def test_repository_persists_crud_and_domain_mapping(database_url: str) -> None:
    database = Database(database_url)
    project_id = uuid4()
    label = Label(uuid4(), project_id, "Backend", "#1A73E8")
    await create_project(database, project_id)

    try:
        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            assert await repository.project_exists(project_id) is True
            assert await repository.create(label) == label
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            assert await repository.get_by_id(label.id) == label
            updated = Label(label.id, project_id, "Platform", "#2563EB")
            assert await repository.update(updated) == updated
            assert await repository.delete(updated.id) is True
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            assert await repository.get_by_id(label.id) is None
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_repository_enforces_foreign_key_and_rolls_back_on_error(database_url: str) -> None:
    database = Database(database_url)
    try:
        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            orphan = Label(uuid4(), uuid4(), "Orphan", "#DC2626")

            with pytest.raises(IntegrityError):
                await repository.create(orphan)

            await session.rollback()
            assert await repository.get_by_id(orphan.id) is None
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_deleting_a_project_cascades_to_its_labels(database_url: str) -> None:
    database = Database(database_url)
    project_id = uuid4()
    label = Label(uuid4(), project_id, "Backend", "#1A73E8")
    await create_project(database, project_id)

    try:
        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            await repository.create(label)
            await session.commit()

        async with database.session_factory() as session:
            project = await session.get(ProjectModel, project_id)
            assert project is not None
            await session.delete(project)
            await session.commit()

        async with database.session_factory() as session:
            assert await SQLAlchemyLabelRepository(session).get_by_id(label.id) is None
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_repository_lists_by_project_and_base_repository_paginates(database_url: str) -> None:
    database = Database(database_url)
    first_project_id = uuid4()
    second_project_id = uuid4()
    await create_project(database, first_project_id)
    await create_project(database, second_project_id)
    first = Label(uuid4(), first_project_id, "Backend", "#1A73E8")
    second = Label(uuid4(), first_project_id, "Bug", "#DC2626")
    other = Label(uuid4(), second_project_id, "Design", "#9333EA")

    try:
        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            for label in (first, second, other):
                await repository.create(label)
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyLabelRepository(session)
            listed = await repository.list_by_project(first_project_id)
            base_repository = BaseRepository(session, LabelModel)
            page = await base_repository.list(offset=1, limit=1)

            assert {label.id for label in listed} == {first.id, second.id}
            assert len(page) == 1
            assert page[0].id in {first.id, second.id, other.id}
    finally:
        await database.dispose()
