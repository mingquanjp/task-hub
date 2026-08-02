"""Global exception handlers for standardizing API responses."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from taskhub.api.schemas import ErrorResponse
from taskhub.core.exceptions import (
    DomainError,
    InactiveUserError,
    IncorrectCurrentPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    PermissionDeniedError,
    ResourceNotFoundError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserNotFoundError,
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
