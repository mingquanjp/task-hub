"""Authentication HTTP endpoints."""

from fastapi import APIRouter, Response, status

from taskhub.api.schemas import ErrorResponse
from taskhub.modules.auth.dependencies import AuthServiceDep, CurrentUserDep
from taskhub.modules.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account. Returns the created user profile without the password.",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Email already exists",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def register(data: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    user = await service.register(str(data.email), data.full_name, data.password)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate a user and return an access token and refresh token pair.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid email or password",
            "model": ErrorResponse,
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User is inactive",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    result = await service.login(str(data.email), data.password)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Obtain a new access token and refresh token pair using a valid refresh token. "
        "The old refresh token is revoked."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid or revoked refresh token",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def refresh(data: RefreshTokenRequest, service: AuthServiceDep) -> TokenResponse:
    result = await service.refresh(data.refresh_token)
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke the provided refresh token. Requires a valid Bearer access token.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid access or refresh token",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def logout(
    user: CurrentUserDep, data: RefreshTokenRequest, service: AuthServiceDep
) -> Response:
    await service.logout(user.id, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
