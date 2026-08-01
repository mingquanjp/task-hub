"""FastAPI dependency wiring for user use cases."""

from typing import Annotated

from fastapi import Depends

from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.dependencies import (
    RefreshTokenRepositoryDep,
    UserRepositoryDep,
)
from taskhub.modules.users.service import UserService


def get_user_service(
    users: UserRepositoryDep,
    refresh_tokens: RefreshTokenRepositoryDep,
) -> UserService:
    return UserService(users, refresh_tokens, PasswordHasher())


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
