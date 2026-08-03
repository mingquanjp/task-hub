"""Workspace API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from taskhub.api.schemas import ErrorResponse
from taskhub.core.exceptions import InvalidWorkspaceRoleError
from taskhub.modules.auth.dependencies import CurrentUserDep
from taskhub.modules.workspaces.dependencies import (
    OwnerWorkspaceUserDep,
    WorkspaceMemberUserDep,
    WorkspaceServiceDep,
)
from taskhub.modules.workspaces.entities import WorkspaceRole
from taskhub.modules.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceMemberInvite,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def create_workspace(
    user: CurrentUserDep,
    data: WorkspaceCreate,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    """Create a new workspace."""
    workspace = await service.create(user, name=data.name)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def get_workspace(
    user: WorkspaceMemberUserDep,
    workspace_id: Annotated[UUID, Path(...)],
    service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Get a workspace by ID."""
    details = await service.get(user, workspace_id)
    return WorkspaceDetailResponse(
        id=details.workspace.id,
        name=details.workspace.name,
        owner_id=details.workspace.owner_id,
        created_at=details.workspace.created_at,
        members=[WorkspaceMemberResponse.model_validate(m) for m in details.members],
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def invite_member(
    user: OwnerWorkspaceUserDep,
    workspace_id: Annotated[UUID, Path(...)],
    data: WorkspaceMemberInvite,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    """Invite a user to a workspace."""
    if data.role == WorkspaceRole.OWNER:
        raise InvalidWorkspaceRoleError("Cannot invite a new owner. Use ownership transfer.")
    member = await service.invite_member(user, workspace_id, data.user_id, data.role)
    return WorkspaceMemberResponse.model_validate(member)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def remove_member(
    user: OwnerWorkspaceUserDep,
    workspace_id: Annotated[UUID, Path(...)],
    user_id: Annotated[UUID, Path(...)],
    service: WorkspaceServiceDep,
) -> None:
    """Remove a user from a workspace."""
    await service.remove_member(user, workspace_id, user_id)
