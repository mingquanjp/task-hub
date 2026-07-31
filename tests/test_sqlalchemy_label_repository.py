"""Unit tests for the SQLAlchemy label persistence adapter."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models import LabelModel
from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.sqlalchemy_repository import SQLAlchemyLabelRepository


def make_session() -> MagicMock:
    """Build an AsyncSession-shaped test double without a database server."""
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_repository_checks_the_project_parent() -> None:
    session = make_session()
    repository = SQLAlchemyLabelRepository(session)
    project_id = uuid4()

    session.scalar.return_value = project_id
    assert await repository.project_exists(project_id) is True

    session.scalar.return_value = None
    assert await repository.project_exists(project_id) is False


@pytest.mark.asyncio
async def test_repository_maps_a_created_domain_entity_to_and_from_orm() -> None:
    session = make_session()
    repository = SQLAlchemyLabelRepository(session)
    label = Label(uuid4(), uuid4(), "Backend", "#1A73E8")

    created = await repository.create(label)

    persisted = session.add.call_args.args[0]
    assert isinstance(persisted, LabelModel)
    assert (persisted.id, persisted.project_id, persisted.name, persisted.color) == (
        label.id,
        label.project_id,
        label.name,
        label.color,
    )
    assert created == label
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_lists_and_gets_domain_entities() -> None:
    session = make_session()
    repository = SQLAlchemyLabelRepository(session)
    label_model = LabelModel(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")
    scalar_result = MagicMock()
    scalar_result.all.return_value = [label_model]
    session.scalars.return_value = scalar_result
    session.get.return_value = label_model

    assert await repository.list_by_project(label_model.project_id) == [
        Label(label_model.id, label_model.project_id, "Backend", "#1A73E8")
    ]
    assert await repository.get_by_id(label_model.id) == Label(
        label_model.id,
        label_model.project_id,
        "Backend",
        "#1A73E8",
    )
    session.get.assert_awaited_once_with(LabelModel, label_model.id)


@pytest.mark.asyncio
async def test_repository_updates_and_deletes_by_entity_id() -> None:
    session = make_session()
    repository = SQLAlchemyLabelRepository(session)
    model = LabelModel(id=uuid4(), project_id=uuid4(), name="Backend", color="#1A73E8")
    session.get.return_value = model
    updated = Label(model.id, model.project_id, "Platform", "#2563EB")

    assert await repository.update(updated) == updated
    assert (model.name, model.color) == ("Platform", "#2563EB")
    assert await repository.delete(model.id) is True
    session.delete.assert_awaited_once_with(model)
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_repository_returns_none_or_false_for_missing_label() -> None:
    session = make_session()
    repository = SQLAlchemyLabelRepository(session)
    session.get.return_value = None

    assert await repository.get_by_id(uuid4()) is None
    assert await repository.delete(uuid4()) is False
