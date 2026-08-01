"""FastAPI dependency wiring for authentication use cases."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from taskhub.api.dependencies import DbSessionDep
from taskhub.core.config import SecuritySettings, get_security_settings
from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.entities import User
from taskhub.modules.auth.repository import (
    RefreshTokenRepository,
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyUserRepository,
    UserRepository,
)
from taskhub.modules.auth.service import AuthService
from taskhub.modules.auth.tokens import InvalidTokenErrorDomain, TokenService

bearer_scheme = HTTPBearer(auto_error=False)


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


def get_token_service(settings: SecuritySettingsDep) -> TokenService:
    return TokenService(settings)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    tokens: TokenServiceDep,
    users: UserRepositoryDep,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        user_id = tokens.decode_access(credentials.credentials)
    except InvalidTokenErrorDomain as exc:
        raise unauthorized from exc

    user = await users.get_by_id(user_id)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
