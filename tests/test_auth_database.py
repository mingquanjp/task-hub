"""Database-backed tests for authentication persistence behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taskhub.infrastructure.database.models import RefreshTokenModel, UserModel, UserRole
from taskhub.infrastructure.database.session import Database
from taskhub.modules.auth.repository import SQLAlchemyRefreshTokenRepository


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
