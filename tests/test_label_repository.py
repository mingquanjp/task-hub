"""Unit tests for in-memory label persistence."""

from uuid import uuid4

import pytest

from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.repository import InMemoryLabelRepository


@pytest.mark.asyncio
async def test_repository_stores_labels_by_project() -> None:
    repository = InMemoryLabelRepository()
    first_project_id = uuid4()
    second_project_id = uuid4()
    first = Label(uuid4(), first_project_id, "Backend", "#1A73E8")
    second = Label(uuid4(), first_project_id, "Bug", "#DC2626")
    other_project_label = Label(uuid4(), second_project_id, "Design", "#9333EA")

    await repository.create(first)
    await repository.create(second)
    await repository.create(other_project_label)

    assert list(await repository.list_by_project(first_project_id)) == [first, second]
    assert await repository.get_by_id(first.id) == first
    assert await repository.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_repository_updates_and_deletes_labels() -> None:
    repository = InMemoryLabelRepository()
    label = Label(uuid4(), uuid4(), "Backend", "#1A73E8")
    updated = Label(label.id, label.project_id, "Platform", "#2563EB")
    await repository.create(label)

    assert await repository.update(updated) == updated
    assert await repository.get_by_id(label.id) == updated
    assert await repository.delete(label.id) is True
    assert await repository.delete(label.id) is False
