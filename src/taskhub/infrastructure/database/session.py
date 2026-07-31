"""Async SQLAlchemy engine and session-factory lifecycle."""

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    """Own an application-scoped async engine and its request session factory."""

    def __init__(self, database_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)
        if self.engine.url.get_backend_name() == "sqlite":
            event.listen(self.engine.sync_engine, "connect", _configure_sqlite_connection)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        """Release connections held by the engine pool during application shutdown."""
        await self.engine.dispose()


def _configure_sqlite_connection(dbapi_connection: object, _: object) -> None:
    """Enable relational constraints and PostgreSQL-compatible now() in SQLite tests."""
    connection = cast(Any, dbapi_connection)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.create_function(
        "now",
        0,
        lambda: datetime.now(UTC).isoformat(),
    )
