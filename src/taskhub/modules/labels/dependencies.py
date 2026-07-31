"""FastAPI dependency wiring for label use cases."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskhub.modules.labels.repository import LabelRepository
from taskhub.modules.labels.service import LabelService
from taskhub.modules.labels.sqlalchemy_repository import SQLAlchemyLabelRepository


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


def get_label_repository(session: DbSessionDep) -> LabelRepository:
    """Build the runtime label repository from the request database session."""
    return SQLAlchemyLabelRepository(session)


LabelRepositoryDep = Annotated[LabelRepository, Depends(get_label_repository)]


def get_label_service(repository: LabelRepositoryDep) -> LabelService:
    """Build the label service from its persistence dependency."""
    return LabelService(repository)


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
