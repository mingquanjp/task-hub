"""Unit tests for the Redis caching logic in TaskService."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

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
def mock_label_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    mock_task_repo: AsyncMock,
    mock_project_repo: AsyncMock,
    mock_label_repo: AsyncMock,
    mock_member_repo: AsyncMock,
    mock_redis: AsyncMock,
) -> TaskService:
    return TaskService(
        mock_task_repo,
        mock_project_repo,
        mock_label_repo,
        mock_member_repo,
        mock_redis,
        cache_ttl=60,
    )


@pytest.mark.asyncio
async def test_cache_miss_stores_data(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    project_id = uuid4()
    # Redis cache miss on version, sets version to "1"
    mock_redis.get.side_effect = [None, None]  # version get, tasks get

    task = Task(
        id=uuid4(),
        project_id=project_id,
        assignee_id=None,
        title="Test Task",
        description=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        due_date=None,
        created_by=uuid4(),
        created_at=datetime.now(UTC),
    )
    mock_task_repo.list_by_project.return_value = ([task], 1)

    tasks, total = await service.list_by_project(project_id, page=1, limit=10)

    assert total == 1
    assert len(tasks) == 1

    # Verify redis operations
    mock_redis.set.assert_called_with(f"task_list_version:{project_id}", "1")
    cache_key = f"tasks:{project_id}:v1:any:any:any:1:10"
    mock_redis.get.assert_called_with(cache_key)

    mock_redis.setex.assert_called_once()
    args, _ = mock_redis.setex.call_args
    assert args[0] == cache_key
    assert args[1] == 60  # ttl
    cached_data = json.loads(args[2])
    assert cached_data["total"] == 1
    assert cached_data["tasks"][0]["id"] == str(task.id)


@pytest.mark.asyncio
async def test_cache_hit_skips_db(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    project_id = uuid4()
    task_id = uuid4()
    # Return version "2"
    version_bytes = b"2"

    cached_payload = json.dumps(
        {
            "total": 5,
            "tasks": [
                {
                    "id": str(task_id),
                    "project_id": str(project_id),
                    "assignee_id": None,
                    "title": "Cached Task",
                    "description": None,
                    "status": "TODO",
                    "priority": "LOW",
                    "due_date": None,
                    "created_by": str(uuid4()),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ],
        }
    )

    mock_redis.get.side_effect = [version_bytes, cached_payload.encode("utf-8")]

    tasks, total = await service.list_by_project(project_id, page=1, limit=10)

    assert total == 5
    assert len(tasks) == 1
    assert tasks[0].title == "Cached Task"

    # Verify db was NOT called
    mock_task_repo.list_by_project.assert_not_called()


@pytest.mark.asyncio
async def test_cache_invalidation_on_mutation(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_project_repo: AsyncMock,
    mock_member_repo: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    project_id = uuid4()

    # Setup for create
    mock_project_repo.get_by_id.return_value = Project(
        id=project_id,
        workspace_id=uuid4(),
        name="Project",
        description="",
        status=ProjectStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )
    mock_task_repo.create.return_value = Task(
        id=uuid4(),
        project_id=project_id,
        assignee_id=None,
        title="Task",
        description=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        due_date=None,
        created_by=uuid4(),
        created_at=datetime.now(UTC),
    )

    await service.create(
        project_id=project_id,
        creator_id=uuid4(),
        title="Task",
        description="Desc",
        priority=TaskPriority.LOW,
    )

    mock_redis.incr.assert_called_once_with(f"task_list_version:{project_id}")


@pytest.mark.asyncio
async def test_cache_fallback_on_redis_error(
    service: TaskService,
    mock_task_repo: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    project_id = uuid4()

    # Redis throws error
    mock_redis.get.side_effect = Exception("Redis connection refused")

    mock_task_repo.list_by_project.return_value = ([], 0)

    with patch("taskhub.modules.tasks.service.logger") as mock_logger:
        tasks, total = await service.list_by_project(project_id, page=1, limit=10)

        assert total == 0
        assert len(tasks) == 0

        # Verify db was called
        mock_task_repo.list_by_project.assert_called_once()

        # Verify warning log
        mock_logger.warning.assert_called()
        args, kwargs = mock_logger.warning.call_args
        assert "failed" in args[0]
        assert kwargs["exc_info"] is True
        assert "extra" in kwargs
