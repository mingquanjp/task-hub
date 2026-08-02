"""Unit tests for get_current_user dependency."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from taskhub.core.config import SecuritySettings
from taskhub.core.exceptions import InactiveUserError, InvalidTokenError
from taskhub.modules.auth.dependencies import get_current_user
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.auth.tokens import TokenService


class FakeUserRepository:
    def __init__(self, user: User | None = None) -> None:
        self.user = user

    async def get_by_email(self, email: str) -> User | None:
        return self.user if self.user and self.user.email == email else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.user if self.user and self.user.id == user_id else None

    async def create(self, user: User) -> User:
        self.user = user
        return user

    async def update(self, user: User) -> User:
        self.user = user
        return user


@pytest.fixture
def token_service(security_settings: SecuritySettings) -> TokenService:
    return TokenService(security_settings)


@pytest.fixture
def active_user() -> User:
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="User",
        hashed_password="hash",
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_get_current_user_valid_access_token(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)
    pair = token_service.issue_pair(active_user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=pair.access_token)

    user = await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]
    assert user.id == active_user.id


@pytest.mark.asyncio
async def test_get_current_user_missing_credentials(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)

    with pytest.raises(InvalidTokenError):
        await get_current_user(None, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_non_bearer(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="abc")

    with pytest.raises(InvalidTokenError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_refresh_token_rejected(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)
    pair = token_service.issue_pair(active_user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=pair.refresh_token)

    with pytest.raises(InvalidTokenError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_malformed_jwt(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(InvalidTokenError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_expired_jwt(
    token_service: TokenService,
    active_user: User,
) -> None:
    repo = FakeUserRepository(active_user)
    pair = token_service.issue_pair(active_user.id, now=datetime.now(UTC) - timedelta(days=2))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=pair.access_token)

    with pytest.raises(InvalidTokenError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(
    token_service: TokenService,
) -> None:
    repo = FakeUserRepository(None)
    pair = token_service.issue_pair(uuid4())
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=pair.access_token)

    with pytest.raises(InvalidTokenError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_current_user_inactive(
    token_service: TokenService,
    active_user: User,
) -> None:
    active_user = dataclasses.replace(active_user, is_active=False)
    repo = FakeUserRepository(active_user)
    pair = token_service.issue_pair(active_user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=pair.access_token)

    with pytest.raises(InactiveUserError):
        await get_current_user(credentials, token_service, repo)  # type: ignore[arg-type]
