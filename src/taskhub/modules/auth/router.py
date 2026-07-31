"""Authentication HTTP endpoints."""

from fastapi import APIRouter, HTTPException, Response, status

from taskhub.modules.auth.dependencies import AuthServiceDep
from taskhub.modules.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from taskhub.modules.auth.service import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Email already exists"}},
)
async def register(data: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    try:
        user = await service.register(str(data.email), data.full_name, data.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from exc
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
    try:
        result = await service.login(str(data.email), data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        ) from exc
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
    try:
        result = await service.refresh(data.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc
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
    try:
        await service.logout(data.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
