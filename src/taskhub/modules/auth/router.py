"""Authentication HTTP endpoints."""

from fastapi import APIRouter, Response, status

from taskhub.modules.auth.dependencies import AuthServiceDep
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
    responses={status.HTTP_409_CONFLICT: {"description": "Email already exists"}},
)
async def register(data: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    user = await service.register(str(data.email), data.full_name, data.password)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid email or password"},
        status.HTTP_403_FORBIDDEN: {"description": "User is inactive"},
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
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Invalid refresh token"}},
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
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Invalid refresh token"}},
)
async def logout(data: RefreshTokenRequest, service: AuthServiceDep) -> Response:
    await service.logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
