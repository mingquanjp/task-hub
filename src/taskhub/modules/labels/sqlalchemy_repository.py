"""SQLAlchemy adapter for label persistence."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models import LabelModel, ProjectModel
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.labels.entities import Label


class SQLAlchemyLabelRepository:
    """Persist Label domain entities with an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._models = BaseRepository(session, LabelModel)

    async def project_exists(self, project_id: UUID) -> bool:
        """Report whether a project row exists for a label parent."""
        statement = select(ProjectModel.id).where(ProjectModel.id == project_id)
        return await self._session.scalar(statement) is not None

    async def create(self, label: Label) -> Label:
        """Store a domain entity and return its persisted representation."""
        model = LabelModel(
            id=label.id,
            project_id=label.project_id,
            name=label.name,
            color=label.color,
        )
        return self._to_entity(await self._models.add(model))

    async def list_by_project(self, project_id: UUID) -> Sequence[Label]:
        """Return labels belonging to one project."""
        statement = (
            select(LabelModel).where(LabelModel.project_id == project_id).order_by(LabelModel.id)
        )
        models = (await self._session.scalars(statement)).all()
        return [self._to_entity(model) for model in models]

    async def get_by_id(self, label_id: UUID) -> Label | None:
        """Return a label domain entity by ID when it exists."""
        model = await self._models.get_by_id(label_id)
        return None if model is None else self._to_entity(model)

    async def update(self, label: Label) -> Label:
        """Persist the complete entity state prepared by the application service."""
        model = await self._models.get_by_id(label.id)
        if model is None:
            raise LookupError("Label was removed before it could be updated")
        model.name = label.name
        model.color = label.color
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, label_id: UUID) -> bool:
        """Delete a label by ID and report whether it existed."""
        model = await self._models.get_by_id(label_id)
        if model is None:
            return False
        await self._models.delete(model)
        return True

    @staticmethod
    def _to_entity(model: LabelModel) -> Label:
        return Label(
            id=model.id,
            project_id=model.project_id,
            name=model.name,
            color=model.color,
        )
