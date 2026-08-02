"""HTTP endpoints for user profile management."""

from fastapi import APIRouter, status

from taskhub.api.schemas import ErrorResponse
from taskhub.modules.auth.dependencies import CurrentUserDep
from taskhub.modules.auth.schemas import UserResponse
from taskhub.modules.users.dependencies import UserServiceDep
from taskhub.modules.users.schemas import ChangePasswordRequest, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the profile of the currently authenticated user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Not authenticated",
            "model": ErrorResponse,
        },
    },
)
async def get_current_user_profile(user: CurrentUserDep) -> UserResponse:
    """Return the currently authenticated user's profile information."""
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update the authenticated user's profile details.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Not authenticated",
            "model": ErrorResponse,
        },
        status.HTTP_409_CONFLICT: {
            "description": "Email already in use",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error (e.g., empty body)",
            "model": ErrorResponse,
        },
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
    description=(
        "Change the password for the currently authenticated user "
        "and revoke all their refresh tokens."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Incorrect current password",
            "model": ErrorResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Not authenticated",
            "model": ErrorResponse,
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
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
