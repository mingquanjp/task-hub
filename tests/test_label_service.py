"""Unit tests for label application use cases."""

from uuid import uuid4

import pytest

from taskhub.modules.labels.repository import InMemoryLabelRepository
from taskhub.modules.labels.schemas import LabelCreate, LabelUpdate
from taskhub.modules.labels.service import LabelNotFoundError, LabelService, ProjectNotFoundError


class MissingProjectRepository(InMemoryLabelRepository):
    """Unit-test adapter that models an absent project parent."""

    async def project_exists(self, project_id: object) -> bool:
        return False


@pytest.mark.asyncio
async def test_service_runs_label_lifecycle_with_partial_updates() -> None:
    repository = InMemoryLabelRepository()
    service = LabelService(repository)
    project_id = uuid4()
    created = await service.create(project_id, LabelCreate(name="Backend", color="#1a73e8"))

    assert created.id is not None
    assert created.project_id == project_id
    assert created.color == "#1A73E8"
    assert await service.list_by_project(project_id) == [created]

    updated = await service.update(project_id, created.id, LabelUpdate(name="Platform"))

    assert updated.name == "Platform"
    assert updated.color == "#1A73E8"
    assert await service.get(project_id, created.id) == updated

    await service.delete(project_id, created.id)
    with pytest.raises(LabelNotFoundError):
        await service.get(project_id, created.id)


@pytest.mark.asyncio
async def test_service_hides_labels_from_other_projects() -> None:
    service = LabelService(InMemoryLabelRepository())
    owner_project_id = uuid4()
    other_project_id = uuid4()
    label = await service.create(owner_project_id, LabelCreate(name="Backend", color="#1A73E8"))

    with pytest.raises(LabelNotFoundError):
        await service.get(other_project_id, label.id)
    with pytest.raises(LabelNotFoundError):
        await service.update(other_project_id, label.id, LabelUpdate(name="Platform"))
    with pytest.raises(LabelNotFoundError):
        await service.delete(other_project_id, label.id)


@pytest.mark.asyncio
async def test_service_rejects_creation_for_a_missing_project() -> None:
    service = LabelService(MissingProjectRepository())

    with pytest.raises(ProjectNotFoundError):
        await service.create(uuid4(), LabelCreate(name="Backend", color="#1A73E8"))
