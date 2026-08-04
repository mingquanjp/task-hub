"""Global exception handlers for standardizing API responses."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from taskhub.api.schemas import ErrorResponse
from taskhub.core.exceptions import (
    CommentNotFoundError,
    CommentPermissionDeniedError,
    DomainError,
    InactiveUserError,
    IncorrectCurrentPasswordError,
    InvalidCredentialsError,
    InvalidProjectStateError,
    InvalidTaskStateError,
    InvalidTokenError,
    InvalidWorkspaceRoleError,
    LabelProjectMismatchError,
    PermissionDeniedError,
    ProjectAlreadyArchivedError,
    ProjectNotFoundError,
    ResourceNotFoundError,
    TaskAssigneeNotFoundError,
    TaskAssigneeNotWorkspaceMemberError,
    TaskLabelAlreadyExistsError,
    TaskLabelNotFoundError,
    TaskNotFoundError,
    TaskProjectNotFoundError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserNotFoundError,
    WorkspaceMemberAlreadyExistsError,
    WorkspaceOwnerRemovalError,
)

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map domain exceptions to standard HTTP responses."""
    request_id = _get_request_id(request)
    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred"
    headers = None

    if isinstance(exc, InvalidCredentialsError):
        status_code = 401
        code = "invalid_credentials"
        message = "Invalid email or password"
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, InvalidTokenError):
        status_code = 401
        code = "invalid_token"
        message = "Invalid or expired token"
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, IncorrectCurrentPasswordError):
        status_code = 400
        code = "incorrect_password"
        message = "Incorrect current password"
    elif isinstance(exc, TokenRevokedError):
        status_code = 401
        code = "token_revoked"
        message = "Token has been revoked"
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, UserNotFoundError):
        status_code = 401
        code = "user_not_found"
        message = "User not found"
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, InactiveUserError):
        status_code = 403
        code = "inactive_user"
        message = "User is inactive"
    elif isinstance(exc, PermissionDeniedError):
        status_code = 403
        code = "permission_denied"
        message = "Permission denied"
    elif isinstance(exc, UserAlreadyExistsError):
        status_code = 409
        code = "user_already_exists"
        message = "Email already exists"
    elif isinstance(exc, ResourceNotFoundError):
        status_code = 404
        code = "resource_not_found"
        message = "Resource not found"
    elif isinstance(exc, WorkspaceMemberAlreadyExistsError):
        status_code = 409
        code = "workspace_member_already_exists"
        message = "User is already a member"
    elif isinstance(exc, WorkspaceOwnerRemovalError):
        status_code = 409
        code = "workspace_owner_removal_forbidden"
        message = "Cannot remove the workspace owner"
    elif isinstance(exc, InvalidWorkspaceRoleError):
        status_code = 422
        code = "invalid_workspace_role"
        message = "Invalid workspace role"
    elif isinstance(exc, ProjectNotFoundError):
        status_code = 404
        code = "project_not_found"
        message = "Project not found"
    elif isinstance(exc, ProjectAlreadyArchivedError):
        status_code = 409
        code = "project_already_archived"
        message = "Project is already archived"
    elif isinstance(exc, (InvalidProjectStateError, InvalidTaskStateError)):
        status_code = 409
        code = "invalid_state"
        message = "Invalid state for operation"
    elif isinstance(exc, TaskNotFoundError):
        status_code = 404
        code = "task_not_found"
        message = "Task not found"
    elif isinstance(exc, TaskAssigneeNotFoundError):
        status_code = 404
        code = "task_assignee_not_found"
        message = "Task assignee not found"
    elif isinstance(exc, TaskAssigneeNotWorkspaceMemberError):
        status_code = 403
        code = "task_assignee_not_workspace_member"
        message = "Assignee is not a member of the workspace"
    elif isinstance(exc, TaskProjectNotFoundError):
        status_code = 404
        code = "task_project_not_found"
        message = "Project for the task not found"
    elif isinstance(exc, CommentNotFoundError):
        status_code = 404
        code = "comment_not_found"
        message = "Comment not found"
    elif isinstance(exc, CommentPermissionDeniedError):
        status_code = 403
        code = "comment_permission_denied"
        message = "You do not have permission to modify this comment"
    elif isinstance(exc, TaskLabelNotFoundError):
        status_code = 404
        code = "task_label_not_found"
        message = "Task label association not found"
    elif isinstance(exc, TaskLabelAlreadyExistsError):
        status_code = 409
        code = "task_label_already_exists"
        message = "Label is already attached to this task"
    elif isinstance(exc, LabelProjectMismatchError):
        status_code = 409
        code = "label_project_mismatch"
        message = "Label belongs to a different project"

    response = ErrorResponse(code=code, message=message, request_id=request_id)
    if headers is None:
        headers = {}
    headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardize Pydantic validation errors."""
    request_id = _get_request_id(request)
    response = ErrorResponse(
        code="validation_error",
        message="Request validation failed",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=422,
        content=response.model_dump(),
        headers={"X-Request-ID": request_id},
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors to prevent leaking details."""
    request_id = _get_request_id(request)

    logger.exception(
        "Unhandled exception in request %s %s",
        request.method,
        request.url.path,
        extra={"request_id": request_id},
    )

    response = ErrorResponse(
        code="internal_error",
        message="An unexpected error occurred",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
        headers={"X-Request-ID": request_id},
    )
