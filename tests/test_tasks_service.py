"""Unit tests for the task service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from taskhub.core.exceptions import (
    InvalidProjectStateError,
    TaskAssigneeNotWorkspaceMemberError,
)
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.tasks.entities import Task, TaskPriority, TaskStatus
from taskhub.modules.tasks.service import TaskService


@pytest.fixture
def mock_task_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_member_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    mock_task_repo: AsyncMock,
    mock_project_repo: AsyncMock,
    mock_member_repo: AsyncMock,
) -> TaskService:
    return TaskService(mock_task_repo, mock_project_repo, mock_member_repo)


@pytest.mark.asyncio
async def test_create_task_success(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_project_repo: AsyncMock,
    mock_member_repo: AsyncMock,
) -> None:
    project_id = uuid4()
    creator_id = uuid4()
    workspace_id = uuid4()
    
    mock_project_repo.get_by_id.return_value = Project(
        project_id, workspace_id, "Proj", None, ProjectStatus.ACTIVE, None
    )
    
    mock_task_repo.create.return_value = Task(
        id=uuid4(),
        project_id=project_id,
        assignee_id=None,
        title="Test Task",
        description=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        due_date=None,
        created_by=creator_id,
        created_at=datetime.now(UTC),
    )

    task = await service.create(project_id, creator_id, "Test Task")

    assert task.title == "Test Task"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM
    mock_task_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_archived_project(
    service: TaskService,
    mock_project_repo: AsyncMock,
) -> None:
    project_id = uuid4()
    mock_project_repo.get_by_id.return_value = Project(
        project_id, uuid4(), "Proj", None, ProjectStatus.ARCHIVED, None
    )

    with pytest.raises(InvalidProjectStateError):
        await service.create(project_id, uuid4(), "Test Task")


@pytest.mark.asyncio
async def test_create_task_assignee_not_member(
    service: TaskService,
    mock_project_repo: AsyncMock,
    mock_member_repo: AsyncMock,
) -> None:
    project_id = uuid4()
    assignee_id = uuid4()
    mock_project_repo.get_by_id.return_value = Project(
        project_id, uuid4(), "Proj", None, ProjectStatus.ACTIVE, None
    )
    mock_member_repo.get.return_value = None

    with pytest.raises(TaskAssigneeNotWorkspaceMemberError):
        await service.create(project_id, uuid4(), "Test Task", assignee_id=assignee_id)


@pytest.mark.asyncio
async def test_update_task_success(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_project_repo: AsyncMock,
) -> None:
    task_id = uuid4()
    project_id = uuid4()
    
    task = Task(
        id=task_id,
        project_id=project_id,
        assignee_id=None,
        title="Old",
        description=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        due_date=None,
        created_by=uuid4(),
        created_at=datetime.now(UTC),
    )
    mock_task_repo.get_by_id.return_value = task
    mock_project_repo.get_by_id.return_value = Project(
        project_id, uuid4(), "Proj", None, ProjectStatus.ACTIVE, None
    )
    
    # We update title and status
    mock_task_repo.update.return_value = task
    
    updated = await service.update(task_id, title="New", status=TaskStatus.IN_PROGRESS)
    
    assert updated.title == "New"
    assert updated.status == TaskStatus.IN_PROGRESS
    mock_task_repo.update.assert_called_once()
