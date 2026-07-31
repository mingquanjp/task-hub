"""FastAPI dependency wiring for authentication use cases."""

from typing import Annotated

from fastapi import Depends, Request

from taskhub.api.dependencies import DbSessionDep
from taskhub.core.config import SecuritySettings, get_security_settings
from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.repository import (
    RefreshTokenRepository,
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyUserRepository,
    UserRepository,
)
from taskhub.modules.auth.service import AuthService
from taskhub.modules.auth.tokens import TokenService


def get_security_configuration(request: Request) -> SecuritySettings:
    """Use a test-provided app setting or load validated environment settings."""
    configured = getattr(request.app.state, "security_settings", None)
    return configured or get_security_settings()


SecuritySettingsDep = Annotated[SecuritySettings, Depends(get_security_configuration)]


def get_user_repository(session: DbSessionDep) -> UserRepository:
    return SQLAlchemyUserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_refresh_token_repository(session: DbSessionDep) -> RefreshTokenRepository:
    return SQLAlchemyRefreshTokenRepository(session)


RefreshTokenRepositoryDep = Annotated[
    RefreshTokenRepository,
    Depends(get_refresh_token_repository),
]


def get_auth_service(
    users: UserRepositoryDep,
    refresh_tokens: RefreshTokenRepositoryDep,
    settings: SecuritySettingsDep,
) -> AuthService:
    return AuthService(users, refresh_tokens, PasswordHasher(), TokenService(settings))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
