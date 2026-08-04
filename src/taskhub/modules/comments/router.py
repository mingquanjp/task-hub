"""HTTP routing for comment endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from taskhub.api.schemas import PaginatedResponse
from taskhub.modules.auth.entities import UserRole
from taskhub.modules.comments.dependencies import CommentServiceDep
from taskhub.modules.comments.schemas import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
)
from taskhub.modules.tasks.dependencies import TaskMemberDep
from taskhub.modules.workspaces.dependencies import WorkspaceMemberRepositoryDep
from taskhub.modules.workspaces.entities import WorkspaceRole

router = APIRouter(tags=["comments"])


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    user_task_project: TaskMemberDep,  # Any workspace member can comment
    task_id: UUID,
    payload: CommentCreate,
    service: CommentServiceDep,
) -> CommentResponse:
    """Create a new comment on a task."""
    user, _, _ = user_task_project
    comment = await service.create(task_id, user.id, payload.content)
    return CommentResponse.model_validate(comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
)
async def list_comments(
    user_task_project: TaskMemberDep,  # Any workspace member can read comments
    task_id: UUID,
    service: CommentServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[CommentResponse]:
    """List comments for a task."""
    offset = (page - 1) * limit
    comments, total = await service.list_by_task(task_id, offset=offset, limit=limit)

    return PaginatedResponse(
        items=[CommentResponse.model_validate(c) for c in comments],
        total=total,
        page=page,
        limit=limit,
    )


@router.patch(
    "/tasks/{task_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment(
    user_task_project: TaskMemberDep,  # Workspace membership check
    task_id: UUID,
    comment_id: UUID,
    payload: CommentUpdate,
    service: CommentServiceDep,
) -> CommentResponse:
    """Update a comment. Only the author can update it."""
    user, _, _ = user_task_project
    comment = await service.update(task_id, comment_id, user.id, payload.content)
    return CommentResponse.model_validate(comment)


@router.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    user_task_project: TaskMemberDep,
    task_id: UUID,
    comment_id: UUID,
    service: CommentServiceDep,
    member_repo: WorkspaceMemberRepositoryDep,
) -> None:
    """Delete a comment. Author, OWNER, or ADMIN can delete."""
    user, _, project = user_task_project

    workspace_role = WorkspaceRole.VIEWER
    is_admin = user.role == UserRole.ADMIN
    if not is_admin:
        member = await member_repo.get(project.workspace_id, user.id)
        if member:
            workspace_role = member.role

    await service.delete(
        task_id=task_id,
        comment_id=comment_id,
        current_user_id=user.id,
        workspace_role=workspace_role,
        is_admin=is_admin,
    )
