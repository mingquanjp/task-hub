"""Generic SQLAlchemy persistence operations with no domain rules."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.base import Base


class BaseRepository[TModel: Base]:
    """Provide common persistence operations for UUID-backed ORM models."""

    max_limit = 100

    def __init__(self, session: AsyncSession, model_type: type[TModel]) -> None:
        self._session = session
        self._model_type = model_type

    async def add(self, model: TModel) -> TModel:
        """Add a model and flush it without committing the transaction."""
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_by_id(self, model_id: UUID) -> TModel | None:
        """Return a model by primary key when it exists."""
        return await self._session.get(self._model_type, model_id)

    async def delete(self, model: TModel) -> None:
        """Delete a model and flush without committing the transaction."""
        await self._session.delete(model)
        await self._session.flush()

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[TModel]:
        """Return one validated page of models without domain-specific filtering."""
        self._validate_page(offset=offset, limit=limit)
        statement = (
            select(self._model_type)
            .order_by(*self._model_type.__table__.primary_key)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return result.all()

    def _validate_page(self, *, offset: int, limit: int) -> None:
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if limit > self.max_limit:
            raise ValueError(f"limit must not exceed {self.max_limit}")
