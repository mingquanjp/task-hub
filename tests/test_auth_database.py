"""Database-backed tests for authentication persistence behavior."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taskhub.infrastructure.database.models import RefreshTokenModel, UserModel, UserRole
from taskhub.infrastructure.database.session import Database
from taskhub.modules.auth.entities import User
from taskhub.modules.auth.repository import (
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyUserRepository,
)


@pytest.mark.asyncio
async def test_refresh_token_revoke_is_atomic_and_one_time(database_url: str) -> None:
    database = Database(database_url)
    user_id = uuid4()
    token_id = uuid4()
    try:
        async with database.session_factory() as session:
            session.add(
                UserModel(
                    id=user_id,
                    email="user@example.com",
                    full_name="User",
                    hashed_password="hash",
                    role=UserRole.MEMBER,
                )
            )
            session.add(
                RefreshTokenModel(
                    id=token_id,
                    user_id=user_id,
                    token_hash="a" * 64,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            )
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyRefreshTokenRepository(session)
            assert await repository.revoke(token_id, datetime.now(UTC)) is True
            assert await repository.revoke(token_id, datetime.now(UTC)) is False
            await session.commit()
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_user_repository_update(database_url: str) -> None:
    database = Database(database_url)
    user_id = uuid4()
    try:
        async with database.session_factory() as session:
            repository = SQLAlchemyUserRepository(session)

            user = User(
                id=user_id,
                email="update@example.com",
                full_name="User",
                hashed_password="hash",
                role=UserRole.MEMBER,
                is_active=True,
                created_at=datetime.now(UTC),
            )
            await repository.create(user)
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyUserRepository(session)
            user_to_update = await repository.get_by_id(user_id)
            assert user_to_update is not None

            user_to_update = dataclasses.replace(
                user_to_update,
                full_name="Updated User",
                email="new_update@example.com",
            )

            await repository.update(user_to_update)
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyUserRepository(session)
            updated = await repository.get_by_id(user_id)
            assert updated is not None
            assert updated.full_name == "Updated User"
            assert updated.email == "new_update@example.com"
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_refresh_token_revoke_all_for_user(database_url: str) -> None:
    database = Database(database_url)
    user_id = uuid4()
    try:
        async with database.session_factory() as session:
            session.add(
                UserModel(
                    id=user_id,
                    email="revoke_all@example.com",
                    full_name="User",
                    hashed_password="hash",
                    role=UserRole.MEMBER,
                )
            )
            for i in range(3):
                session.add(
                    RefreshTokenModel(
                        id=uuid4(),
                        user_id=user_id,
                        token_hash=f"hash{i}",
                        expires_at=datetime.now(UTC) + timedelta(days=7),
                    )
                )
            await session.commit()

        async with database.session_factory() as session:
            repository = SQLAlchemyRefreshTokenRepository(session)
            count = await repository.revoke_all_for_user(user_id, datetime.now(UTC))
            assert count == 3

            # Subsquent revokes should return 0
            count_again = await repository.revoke_all_for_user(user_id, datetime.now(UTC))
            assert count_again == 0
            await session.commit()
    finally:
        await database.dispose()
