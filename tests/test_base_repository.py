"""Unit tests for common SQLAlchemy repository operations."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models import LabelModel
from taskhub.infrastructure.repositories.base import BaseRepository


def make_session() -> MagicMock:
    """Build an async-session-shaped test double without a database server."""
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.delete = AsyncMock()
    session.scalars = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_base_repository_adds_and_flushes_a_model() -> None:
    session = make_session()
    repository = BaseRepository(session, LabelModel)
    label = LabelModel(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")

    assert await repository.add(label) is label
    session.add.assert_called_once_with(label)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_base_repository_gets_and_deletes_a_model() -> None:
    session = make_session()
    repository = BaseRepository(session, LabelModel)
    label_id = uuid4()
    label = LabelModel(id=label_id, project_id=uuid4(), name="Backend", color="#1A73E8")
    session.get.return_value = label

    assert await repository.get_by_id(label_id) is label
    session.get.assert_awaited_once_with(LabelModel, label_id)

    await repository.delete(label)
    session.delete.assert_awaited_once_with(label)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_base_repository_lists_a_valid_page() -> None:
    session = make_session()
    repository = BaseRepository(session, LabelModel)
    labels = [LabelModel(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")]
    scalar_result = MagicMock()
    scalar_result.all.return_value = labels
    session.scalars.return_value = scalar_result

    assert await repository.list(offset=2, limit=10) == labels
    session.scalars.assert_awaited_once()
    statement = session.scalars.await_args.args[0]
    compiled = statement.compile()
    assert "ORDER BY labels.id" in str(statement)
    assert "LIMIT :param_1 OFFSET :param_2" in str(statement)
    assert compiled.params == {"param_1": 10, "param_2": 2}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "limit", "message"),
    [
        (-1, 1, "offset"),
        (0, 0, "limit must be greater"),
        (0, 101, "limit must not exceed"),
    ],
)
async def test_base_repository_rejects_an_invalid_page(
    offset: int,
    limit: int,
    message: str,
) -> None:
    session = make_session()
    repository = BaseRepository(session, LabelModel)

    with pytest.raises(ValueError, match=message):
        await repository.list(offset=offset, limit=limit)

    session.scalars.assert_not_awaited()
