"""Authentication persistence contracts and SQLAlchemy adapters."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models import RefreshTokenModel, UserModel
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.auth.entities import RefreshToken, User


class UserRepository(Protocol):
    """Persistence operations required by authentication use cases."""

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def create(self, user: User) -> User: ...

    async def update(self, user: User) -> User: ...


class RefreshTokenRepository(Protocol):
    """Persistence operations required by refresh-token lifecycle management."""

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def create(self, token: RefreshToken) -> RefreshToken: ...

    async def revoke(self, token_id: UUID, revoked_at: datetime) -> bool: ...

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> int: ...


class DuplicateEmailPersistenceError(Exception):
    """Raised when the database unique email index rejects a concurrent insert."""


class SQLAlchemyUserRepository:
    """Map User domain entities to SQLAlchemy models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._models = BaseRepository(session, UserModel)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email)
        model = await self._session.scalar(statement)
        return None if model is None else self._to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._models.get_by_id(user_id)
        return None if model is None else self._to_entity(model)

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        try:
            return self._to_entity(await self._models.add(model))
        except IntegrityError as exc:
            # The request-scoped DB dependency owns rollback after this domain error propagates.
            raise DuplicateEmailPersistenceError from exc

    async def update(self, user: User) -> User:
        statement = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                email=user.email,
                full_name=user.full_name,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=user.is_active,
            )
        )
        try:
            await self._session.execute(statement)
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateEmailPersistenceError from exc
        return user

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            hashed_password=model.hashed_password,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
        )


class SQLAlchemyRefreshTokenRepository:
    """Map refresh-token lifecycle operations to SQLAlchemy models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._models = BaseRepository(session, RefreshTokenModel)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        model = await self._session.scalar(statement)
        return None if model is None else self._to_entity(model)

    async def create(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            created_at=token.created_at,
        )
        return self._to_entity(await self._models.add(model))

    async def revoke(self, token_id: UUID, revoked_at: datetime) -> bool:
        statement = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.id == token_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        return getattr(result, "rowcount", 0) == 1

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> int:
        statement = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        return getattr(result, "rowcount", 0)

    @staticmethod
    def _to_entity(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            created_at=model.created_at,
        )
