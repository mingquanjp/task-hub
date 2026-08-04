"""Unit tests for user profile use cases."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from taskhub.core.exceptions import (
    IncorrectCurrentPasswordError,
    UserAlreadyExistsError,
)
from taskhub.core.passwords import PasswordHasher
from taskhub.modules.auth.entities import RefreshToken, User, UserRole
from taskhub.modules.auth.repository import DuplicateEmailPersistenceError
from taskhub.modules.users.service import UserService


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.should_raise_duplicate = False

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def create(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def update(self, user: User) -> User:
        if self.should_raise_duplicate:
            raise DuplicateEmailPersistenceError
        self.users[user.id] = user
        return user


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[UUID, RefreshToken] = {}
        self.revoke_all_called_for: UUID | None = None

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.tokens.values() if t.token_hash == token_hash), None)

    async def create(self, token: RefreshToken) -> RefreshToken:
        self.tokens[token.id] = token
        return token

    async def revoke(self, token_id: UUID, revoked_at: datetime) -> bool:
        if token_id in self.tokens and self.tokens[token_id].revoked_at is None:
            self.tokens[token_id].revoked_at = revoked_at  # type: ignore
            return True
        return False

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> int:
        self.revoke_all_called_for = user_id
        count = 0
        for token in self.tokens.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = revoked_at  # type: ignore
                count += 1
        return count


@pytest.fixture
def users_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def tokens_repo() -> InMemoryRefreshTokenRepository:
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def service(
    users_repo: InMemoryUserRepository, tokens_repo: InMemoryRefreshTokenRepository
) -> UserService:
    return UserService(users_repo, tokens_repo, PasswordHasher())


@pytest.mark.asyncio
async def test_update_profile_success(
    users_repo: InMemoryUserRepository, service: UserService
) -> None:
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Old Name",
        hashed_password="hash",
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    await users_repo.create(user)

    updated = await service.update_profile(
        user.id,
        full_name="New Name",
        email=" NEW@example.com ",
    )
    assert updated.full_name == "New Name"
    assert updated.email == "new@example.com"

    # Check it actually updated
    fetched = await users_repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.full_name == "New Name"


@pytest.mark.asyncio
async def test_update_profile_duplicate_email(
    users_repo: InMemoryUserRepository, service: UserService
) -> None:
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Name",
        hashed_password="hash",
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    await users_repo.create(user)
    users_repo.should_raise_duplicate = True

    with pytest.raises(UserAlreadyExistsError):
        await service.update_profile(user.id, email="other@example.com")


@pytest.mark.asyncio
async def test_change_password_success(
    users_repo: InMemoryUserRepository,
    tokens_repo: InMemoryRefreshTokenRepository,
    service: UserService,
) -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("current-password")

    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Name",
        hashed_password=hashed,
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    await users_repo.create(user)

    await service.change_password(user.id, "current-password", "new-password")

    fetched = await users_repo.get_by_id(user.id)
    assert fetched is not None
    assert hasher.verify("new-password", fetched.hashed_password)
    assert tokens_repo.revoke_all_called_for == user.id


@pytest.mark.asyncio
async def test_change_password_incorrect(
    users_repo: InMemoryUserRepository, service: UserService
) -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("current-password")

    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Name",
        hashed_password=hashed,
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    await users_repo.create(user)

    with pytest.raises(IncorrectCurrentPasswordError):
        await service.change_password(user.id, "wrong-password", "new-password")
