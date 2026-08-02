"""Application use cases for project labels."""

from dataclasses import replace
from uuid import UUID, uuid4

from taskhub.core.exceptions import ResourceNotFoundError
from taskhub.modules.labels.entities import Label
from taskhub.modules.labels.repository import LabelRepository
from taskhub.modules.labels.schemas import LabelCreate, LabelUpdate


class LabelService:
    """Coordinate label use cases independently from HTTP delivery."""

    def __init__(self, repository: LabelRepository) -> None:
        self._repository = repository

    async def create(self, project_id: UUID, data: LabelCreate) -> Label:
        """Create a label in a project."""
        if not await self._repository.project_exists(project_id):
            raise ResourceNotFoundError
        label = Label(
            id=uuid4(),
            project_id=project_id,
            name=data.name,
            color=data.color,
        )
        return await self._repository.create(label)

    async def list_by_project(self, project_id: UUID) -> list[Label]:
        """List labels in a project."""
        return list(await self._repository.list_by_project(project_id))

    async def get(self, project_id: UUID, label_id: UUID) -> Label:
        """Get a label only when it belongs to the requested project."""
        return await self._get_in_project(project_id, label_id)

    async def update(self, project_id: UUID, label_id: UUID, data: LabelUpdate) -> Label:
        """Update only fields explicitly supplied in a partial update."""
        label = await self._get_in_project(project_id, label_id)
        return await self._repository.update(replace(label, **data.model_dump(exclude_unset=True)))

    async def delete(self, project_id: UUID, label_id: UUID) -> None:
        """Delete a label only when it belongs to the requested project."""
        await self._get_in_project(project_id, label_id)
        await self._repository.delete(label_id)

    async def _get_in_project(self, project_id: UUID, label_id: UUID) -> Label:
        label = await self._repository.get_by_id(label_id)
        if label is None or label.project_id != project_id:
            raise ResourceNotFoundError
        return label
