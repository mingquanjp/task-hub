"""Unit tests for authentication use cases with fake repositories."""

from dataclasses import replace
from datetime import datetime

import pytest
from pydantic import SecretStr

from taskhub.core.config import SecuritySettings
from taskhub.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.entities import User
from taskhub.modules.auth.service import AuthService
from taskhub.modules.auth.tokens import TokenService


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def get_by_id(self, user_id: object) -> User | None:
        return next((user for user in self.users.values() if user.id == user_id), None)

    async def create(self, user: User) -> User:
        self.users[str(user.id)] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[str, object] = {}

    async def get_by_hash(self, token_hash: str) -> object:
        return self.tokens.get(token_hash)

    async def create(self, token: object) -> object:
        self.tokens[token.token_hash] = token
        return token

    async def revoke(self, token_id: object, revoked_at: datetime) -> bool:
        for token in self.tokens.values():
            if token.id == token_id:
                self.tokens[token.token_hash] = replace(token, revoked_at=revoked_at)
                return True
        return False


def make_service() -> tuple[AuthService, FakeUserRepository, FakeRefreshTokenRepository]:
    users = FakeUserRepository()
    tokens = FakeRefreshTokenRepository()

    service = AuthService(
        users,
        tokens,
        PasswordHasher(),
        TokenService(SecuritySettings(jwt_secret_key=SecretStr("test-secret-key-" + "x" * 32))),
    )
    return service, users, tokens


@pytest.mark.asyncio
async def test_register_normalizes_email_and_hashes_password() -> None:
    service, users, _ = make_service()

    user = await service.register(" User@Example.COM ", "User", "password123")

    assert user.email == "user@example.com"
    assert user.hashed_password != "password123"
    assert await users.get_by_email("user@example.com") == user


@pytest.mark.asyncio
async def test_register_rejects_duplicate_and_login_rejects_invalid_credentials() -> None:
    service, _, _ = make_service()
    await service.register("user@example.com", "User", "password123")

    with pytest.raises(UserAlreadyExistsError):
        await service.register("USER@example.com", "Other", "password123")
    with pytest.raises(InvalidCredentialsError):
        await service.login("user@example.com", "wrong-password")


@pytest.mark.asyncio
async def test_login_refresh_rotates_and_logout_revokes_token() -> None:
    service, _, tokens = make_service()
    user = await service.register("user@example.com", "User", "password123")

    result = await service.login(user.email, "password123")
    rotated = await service.refresh(result.refresh_token)
    assert rotated.refresh_token != result.refresh_token
    assert len(tokens.tokens) == 2

    with pytest.raises(TokenRevokedError):
        await service.refresh(result.refresh_token)

    await service.logout(rotated.refresh_token)
    with pytest.raises(TokenRevokedError):
        await service.refresh(rotated.refresh_token)


@pytest.mark.asyncio
async def test_inactive_user_cannot_login() -> None:
    service, users, _ = make_service()
    user = await service.register("user@example.com", "User", "password123")
    users.users[str(user.id)] = replace(user, is_active=False)

    with pytest.raises(InactiveUserError):
        await service.login(user.email, "password123")
