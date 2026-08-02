"""FastAPI dependency wiring for workspace use cases."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path

from taskhub.api.dependencies import DbSessionDep
from taskhub.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from taskhub.modules.auth.dependencies import CurrentUserDep, UserRepositoryDep
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.workspaces.entities import WorkspaceRole
from taskhub.modules.workspaces.repository import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from taskhub.modules.workspaces.service import WorkspaceService
from taskhub.modules.workspaces.sqlalchemy_repository import (
    SQLAlchemyWorkspaceMemberRepository,
    SQLAlchemyWorkspaceRepository,
)


def get_workspace_repository(session: DbSessionDep) -> WorkspaceRepository:
    return SQLAlchemyWorkspaceRepository(session)


WorkspaceRepositoryDep = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]


def get_workspace_member_repository(session: DbSessionDep) -> WorkspaceMemberRepository:
    return SQLAlchemyWorkspaceMemberRepository(session)


WorkspaceMemberRepositoryDep = Annotated[
    WorkspaceMemberRepository, Depends(get_workspace_member_repository)
]


def get_workspace_service(
    workspace_repo: WorkspaceRepositoryDep,
    member_repo: WorkspaceMemberRepositoryDep,
    user_repo: UserRepositoryDep,
) -> WorkspaceService:
    return WorkspaceService(
        workspace_repo=workspace_repo,
        member_repo=member_repo,
        user_repo=user_repo,
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


async def require_workspace_member(
    workspace_id: Annotated[UUID, Path(...)],
    user: CurrentUserDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> User:
    """Ensure the current user is a member of the workspace or an ADMIN.

    Raises:
        ResourceNotFoundError: If the workspace does not exist.
        PermissionDeniedError: If the user is not a member and not an ADMIN.
    """
    result = await workspace_repo.get_by_id_with_members(workspace_id)
    if not result:
        raise ResourceNotFoundError("Workspace not found")

    _, members = result

    if user.role == UserRole.ADMIN:
        return user

    is_member = any(m.user_id == user.id for m in members)
    if not is_member:
        raise PermissionDeniedError("Not a member of this workspace")

    return user


WorkspaceMemberUserDep = Annotated[User, Depends(require_workspace_member)]


def require_workspace_role(*allowed_roles: WorkspaceRole) -> Callable[..., Awaitable[User]]:
    """Create a dependency that requires the user to have one of the specified roles."""

    async def _require_role(
        workspace_id: Annotated[UUID, Path(...)],
        user: CurrentUserDep,
        workspace_repo: WorkspaceRepositoryDep,
    ) -> User:
        result = await workspace_repo.get_by_id_with_members(workspace_id)
        if not result:
            raise ResourceNotFoundError("Workspace not found")

        _, members = result

        if user.role == UserRole.ADMIN:
            return user

        member = next((m for m in members if m.user_id == user.id), None)
        if not member:
            raise PermissionDeniedError("Not a member of this workspace")

        if member.role not in allowed_roles:
            raise PermissionDeniedError("Not enough permissions in this workspace")

        return user

    return _require_role


OwnerWorkspaceUserDep = Annotated[User, Depends(require_workspace_role(WorkspaceRole.OWNER))]
