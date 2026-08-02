"""HTTP endpoints for user profile management."""

from fastapi import APIRouter, HTTPException, status

from taskhub.modules.auth.dependencies import CurrentUserDep
from taskhub.modules.auth.schemas import UserResponse
from taskhub.modules.users.dependencies import UserServiceDep
from taskhub.modules.users.schemas import ChangePasswordRequest, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(user: CurrentUserDep) -> UserResponse:
    """Return the currently authenticated user's profile information."""
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    responses={
        409: {"description": "Email already in use"},
        422: {"description": "Validation error (e.g., empty body)"},
    },
)
async def update_current_user_profile(
    user: CurrentUserDep,
    update_data: UserProfileUpdate,
    service: UserServiceDep,
) -> UserResponse:
    """Update the currently authenticated user's profile."""

    updated_user = await service.update_profile(
        user_id=user.id,
        full_name=update_data.full_name,
        email=update_data.email,
    )
    return UserResponse.model_validate(updated_user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change user password",
    responses={
        400: {"description": "Incorrect current password"},
    },
)
async def change_current_user_password(
    user: CurrentUserDep,
    request: ChangePasswordRequest,
    service: UserServiceDep,
) -> None:
    """Change the password for the currently authenticated user and revoke all refresh tokens."""
    await service.change_password(
        user_id=user.id,
        current_password=request.current_password,
        new_password=request.new_password,
    )
