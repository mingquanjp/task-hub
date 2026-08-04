"""FastAPI dependency wiring for project use cases."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path

from taskhub.api.dependencies import DbSessionDep
from taskhub.core.exceptions import ResourceNotFoundError
from taskhub.modules.auth.dependencies import CurrentUserDep
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.projects.entities import Project
from taskhub.modules.projects.repository import ProjectRepository
from taskhub.modules.projects.service import ProjectService
from taskhub.modules.projects.sqlalchemy_repository import SQLAlchemyProjectRepository
from taskhub.modules.workspaces.dependencies import (
    WorkspaceMemberRepositoryDep,
    WorkspaceRepositoryDep,
)
from taskhub.modules.workspaces.entities import WorkspaceRole


def get_project_repository(session: DbSessionDep) -> ProjectRepository:
    """Provide the project repository."""
    return SQLAlchemyProjectRepository(session)


ProjectRepositoryDep = Annotated[ProjectRepository, Depends(get_project_repository)]


def get_project_service(
    project_repo: ProjectRepositoryDep,
) -> ProjectService:
    """Provide the project service."""
    return ProjectService(project_repo)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


async def get_project_or_404(
    project_id: Annotated[UUID, Path(...)],
    project_repo: ProjectRepositoryDep,
) -> Project:
    """Get a project by ID or raise a 404."""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise ResourceNotFoundError(f"Project {project_id} not found")
    return project


ProjectDep = Annotated[Project, Depends(get_project_or_404)]


async def require_project_member(
    user: CurrentUserDep,
    project: ProjectDep,
    workspace_repo: WorkspaceRepositoryDep,
    member_repo: WorkspaceMemberRepositoryDep,
) -> tuple[User, Project]:
    """Ensure the user is a member of the project's workspace (or an ADMIN)."""
    # Verify the workspace exists
    workspace = await workspace_repo.get_by_id(project.workspace_id)
    if not workspace:
        raise ResourceNotFoundError("Workspace not found")

    # ADMIN bypass
    if user.role == UserRole.ADMIN:
        return user, project

    # Verify membership
    member = await member_repo.get(workspace.id, user.id)
    if not member:
        # We raise ResourceNotFoundError for non-members as per typical workspace policy
        # to prevent exposing the existence of the resource.
        # The prompt says: "User không thuộc workspace: 403 hoặc 404 theo policy đã
        # dùng trong Workspace."
        # Let's import PermissionDeniedError.
        from taskhub.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError("User is not a member of this workspace")

    return user, project


ProjectMemberDep = Annotated[tuple[User, Project], Depends(require_project_member)]


def require_project_role(
    *allowed_roles: WorkspaceRole,
) -> Callable[..., Awaitable[tuple[User, Project]]]:
    """
    Create a dependency that requires the user to have one of the specified
    roles in the project's workspace.
    """

    async def _require_role(
        user: CurrentUserDep,
        project: ProjectDep,
        workspace_repo: WorkspaceRepositoryDep,
        member_repo: WorkspaceMemberRepositoryDep,
    ) -> tuple[User, Project]:
        # Verify the workspace exists
        workspace = await workspace_repo.get_by_id(project.workspace_id)
        if not workspace:
            raise ResourceNotFoundError("Workspace not found")

        # ADMIN bypass
        if user.role == UserRole.ADMIN:
            return user, project

        # Verify membership and role
        member = await member_repo.get(workspace.id, user.id)

        from taskhub.core.exceptions import PermissionDeniedError

        if not member:
            raise PermissionDeniedError("User is not a member of this workspace")

        if member.role not in allowed_roles:
            raise PermissionDeniedError("User does not have required permissions")

        return user, project

    return _require_role


# Specific role aliases for convenience
OwnerProjectUserDep = Annotated[
    tuple[User, Project],
    Depends(require_project_role(WorkspaceRole.OWNER)),
]

OwnerOrEditorProjectUserDep = Annotated[
    tuple[User, Project],
    Depends(require_project_role(WorkspaceRole.OWNER, WorkspaceRole.EDITOR)),
]
