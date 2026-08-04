"""Tests for the SQLAlchemy task repository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from taskhub.infrastructure.database.models import ProjectModel, UserModel, WorkspaceModel
from taskhub.infrastructure.database.session import Database
from taskhub.modules.projects.entities import ProjectStatus
from taskhub.modules.tasks.entities import Task, TaskPriority, TaskStatus
from taskhub.modules.tasks.sqlalchemy_repository import SQLAlchemyTaskRepository


async def setup_environment(database: Database) -> tuple[UUID, UUID, UUID]:
    """Create a user, workspace, and project, returning their IDs."""
    user_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()

    async with database.session_factory() as session:
        session.add(
            UserModel(
                id=user_id, email=f"{user_id}@test.com", hashed_password="hash", full_name="Test"
            )
        )
        session.add(WorkspaceModel(id=workspace_id, name="Test WS", owner_id=user_id))
        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                name="Test Project",
                status=ProjectStatus.ACTIVE.value,
            )
        )
        await session.commit()
    return user_id, workspace_id, project_id


@pytest.mark.asyncio
async def test_repository_crud(database_url: str) -> None:
    database = Database(database_url)
    user_id, _, project_id = await setup_environment(database)

    task = Task(
        id=uuid4(),
        project_id=project_id,
        assignee_id=None,
        title="Test Task",
        description="Desc",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        due_date=None,
        created_by=user_id,
        created_at=datetime.now(UTC),
    )

    # Create
    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        created = await repo.create(task)
        await session.commit()

    assert created.id == task.id
    assert created.title == "Test Task"
    assert created.priority == TaskPriority.HIGH

    # Get
    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        retrieved = await repo.get_by_id(task.id)

    assert retrieved is not None
    assert retrieved.title == "Test Task"

    # Update
    task.title = "Updated Task"
    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        updated = await repo.update(task)
        await session.commit()

    assert updated.title == "Updated Task"

    # Delete
    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        await repo.delete(task.id)
        await session.commit()

    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        deleted = await repo.get_by_id(task.id)

    assert deleted is None


@pytest.mark.asyncio
async def test_list_by_project_filtering(database_url: str) -> None:
    database = Database(database_url)
    user_id, _, project_id = await setup_environment(database)

    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)
        # Create 3 tasks with different statuses/priorities
        t1 = Task(
            id=uuid4(),
            project_id=project_id,
            assignee_id=None,
            title="T1",
            description=None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            due_date=None,
            created_by=user_id,
            created_at=datetime.now(UTC),
        )
        t2 = Task(
            id=uuid4(),
            project_id=project_id,
            assignee_id=None,
            title="T2",
            description=None,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=None,
            created_by=user_id,
            created_at=datetime.now(UTC),
        )
        t3 = Task(
            id=uuid4(),
            project_id=project_id,
            assignee_id=user_id,
            title="T3",
            description=None,
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            due_date=None,
            created_by=user_id,
            created_at=datetime.now(UTC),
        )

        await repo.create(t1)
        await repo.create(t2)
        await repo.create(t3)
        await session.commit()

    async with database.session_factory() as session:
        repo = SQLAlchemyTaskRepository(session)

        # Test basic list
        tasks, total = await repo.list_by_project(project_id)
        assert total == 3
        assert len(tasks) == 3

        # Test status filter
        tasks, total = await repo.list_by_project(project_id, status=TaskStatus.IN_PROGRESS)
        assert total == 1
        assert tasks[0].title == "T2"

        # Test priority filter
        tasks, total = await repo.list_by_project(project_id, priority=TaskPriority.HIGH)
        assert total == 2

        # Test assignee filter
        tasks, total = await repo.list_by_project(project_id, assignee_id=user_id)
        assert total == 1
        assert tasks[0].title == "T3"

        # Test pagination
        tasks, total = await repo.list_by_project(project_id, limit=1)
        assert total == 3
        assert len(tasks) == 1
