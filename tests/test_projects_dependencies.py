"""Tests for project dependencies."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from taskhub.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.projects.dependencies import (
    get_project_or_404,
    require_project_member,
    require_project_role,
)
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole


@pytest.fixture
def mock_project_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_workspace_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_member_repo() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_project_or_404_success(mock_project_repo: AsyncMock) -> None:
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    mock_project_repo.get_by_id.return_value = project

    result = await get_project_or_404(project.id, mock_project_repo)
    assert result == project


@pytest.mark.asyncio
async def test_get_project_or_404_raises(mock_project_repo: AsyncMock) -> None:
    mock_project_repo.get_by_id.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await get_project_or_404(uuid4(), mock_project_repo)


@pytest.mark.asyncio
async def test_require_project_member_admin_bypass(
    mock_workspace_repo: AsyncMock, mock_member_repo: AsyncMock
) -> None:
    user = User(uuid4(), "admin@test.com", "Admin", "hash", UserRole.ADMIN, True, None)  # type: ignore
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    workspace = Workspace(project.workspace_id, "WS", uuid4(), None)  # type: ignore

    mock_workspace_repo.get_by_id.return_value = workspace

    u, p = await require_project_member(user, project, mock_workspace_repo, mock_member_repo)
    assert u == user
    assert p == project


@pytest.mark.asyncio
async def test_require_project_member_success(
    mock_workspace_repo: AsyncMock, mock_member_repo: AsyncMock
) -> None:
    user = User(uuid4(), "user@test.com", "User", "hash", UserRole.MEMBER, True, None)  # type: ignore
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    workspace = Workspace(project.workspace_id, "WS", uuid4(), None)  # type: ignore
    member = WorkspaceMember(workspace.id, user.id, WorkspaceRole.VIEWER, None)  # type: ignore

    mock_workspace_repo.get_by_id.return_value = workspace
    mock_member_repo.get.return_value = member

    u, p = await require_project_member(user, project, mock_workspace_repo, mock_member_repo)
    assert u == user
    assert p == project


@pytest.mark.asyncio
async def test_require_project_member_denied(
    mock_workspace_repo: AsyncMock, mock_member_repo: AsyncMock
) -> None:
    user = User(uuid4(), "user@test.com", "User", "hash", UserRole.MEMBER, True, None)  # type: ignore
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    workspace = Workspace(project.workspace_id, "WS", uuid4(), None)  # type: ignore

    mock_workspace_repo.get_by_id.return_value = workspace
    mock_member_repo.get.return_value = None

    with pytest.raises(PermissionDeniedError):
        await require_project_member(user, project, mock_workspace_repo, mock_member_repo)


@pytest.mark.asyncio
async def test_require_project_role_success(
    mock_workspace_repo: AsyncMock, mock_member_repo: AsyncMock
) -> None:
    user = User(uuid4(), "user@test.com", "User", "hash", UserRole.MEMBER, True, None)  # type: ignore
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    workspace = Workspace(project.workspace_id, "WS", uuid4(), None)  # type: ignore
    member = WorkspaceMember(workspace.id, user.id, WorkspaceRole.EDITOR, None)  # type: ignore

    mock_workspace_repo.get_by_id.return_value = workspace
    mock_member_repo.get.return_value = member

    dep = require_project_role(WorkspaceRole.EDITOR)
    u, p = await dep(user, project, mock_workspace_repo, mock_member_repo)
    assert u == user


@pytest.mark.asyncio
async def test_require_project_role_denied(
    mock_workspace_repo: AsyncMock, mock_member_repo: AsyncMock
) -> None:
    user = User(uuid4(), "user@test.com", "User", "hash", UserRole.MEMBER, True, None)  # type: ignore
    project = Project(uuid4(), uuid4(), "Proj", None, ProjectStatus.ACTIVE, None)  # type: ignore
    workspace = Workspace(project.workspace_id, "WS", uuid4(), None)  # type: ignore
    member = WorkspaceMember(workspace.id, user.id, WorkspaceRole.VIEWER, None)  # type: ignore

    mock_workspace_repo.get_by_id.return_value = workspace
    mock_member_repo.get.return_value = member

    dep = require_project_role(WorkspaceRole.EDITOR)
    with pytest.raises(PermissionDeniedError):
        await dep(user, project, mock_workspace_repo, mock_member_repo)
