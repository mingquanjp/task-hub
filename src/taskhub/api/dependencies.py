"""Shared HTTP dependency providers."""

from collections.abc import AsyncIterator
from typing import Annotated, Any, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one transaction-scoped database session per request."""
    session_factory = cast(
        async_sessionmaker[AsyncSession],
        request.app.state.session_factory,
    )
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_redis_client(request: Request) -> Any | None:
    """Provide the Redis client from application state."""
    return getattr(request.app.state, "redis", None)


RedisClientDep = Annotated[Any | None, Depends(get_redis_client)]
