"""Tests for project service."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from taskhub.core.exceptions import (
    ProjectAlreadyArchivedError,
    ProjectNotFoundError,
)
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.projects.service import ProjectService


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_repo: AsyncMock) -> ProjectService:
    return ProjectService(mock_repo)


@pytest.mark.asyncio
async def test_create_project(service: ProjectService, mock_repo: AsyncMock) -> None:
    workspace_id = uuid4()
    mock_repo.create.side_effect = lambda p: p

    project = await service.create(workspace_id, "Proj", "Desc")

    assert project.workspace_id == workspace_id
    assert project.name == "Proj"
    assert project.description == "Desc"
    assert project.status == ProjectStatus.ACTIVE
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_not_found(service: ProjectService, mock_repo: AsyncMock) -> None:
    mock_repo.get_by_id.return_value = None

    with pytest.raises(ProjectNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_update_project_partial(service: ProjectService, mock_repo: AsyncMock) -> None:
    project = Project(uuid4(), uuid4(), "Old", "Old Desc", ProjectStatus.ACTIVE, None)  # type: ignore
    mock_repo.get_by_id.return_value = project
    mock_repo.update.return_value = project

    updated = await service.update(project.id, name="New")

    assert updated.name == "New"
    assert updated.description == "Old Desc"
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_archive_project(service: ProjectService, mock_repo: AsyncMock) -> None:
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    mock_repo.get_by_id.return_value = project
    mock_repo.update.return_value = project

    archived = await service.archive(project.id)
    assert archived.status == ProjectStatus.ARCHIVED


@pytest.mark.asyncio
async def test_archive_already_archived_project(
    service: ProjectService, mock_repo: AsyncMock
) -> None:
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ARCHIVED, None)  # type: ignore
    mock_repo.get_by_id.return_value = project

    with pytest.raises(ProjectAlreadyArchivedError):
        await service.archive(project.id)
