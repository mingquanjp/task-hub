"""SQLAlchemy implementation of the project repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models.project import ProjectModel
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.projects.repository import ProjectRepository


class SQLAlchemyProjectRepository(ProjectRepository):
    """SQLAlchemy implementation of ProjectRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._models = BaseRepository(session, ProjectModel)

    def _to_domain(self, model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            description=model.description,
            status=ProjectStatus(model.status),
            created_at=model.created_at,
        )

    def _to_model(self, entity: Project) -> ProjectModel:
        return ProjectModel(
            id=entity.id,
            workspace_id=entity.workspace_id,
            name=entity.name,
            description=entity.description,
            status=entity.status.value,
            created_at=entity.created_at,
        )

    async def create(self, project: Project) -> Project:
        """Persist a new project."""
        model = self._to_model(project)
        await self._models.add(model)
        return self._to_domain(model)

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get a project by ID."""
        model = await self._models.get_by_id(project_id)
        if model is None:
            return None
        return self._to_domain(model)

    async def list_by_workspace(self, workspace_id: UUID) -> list[Project]:
        """List all projects in a workspace."""
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.workspace_id == workspace_id)
            .order_by(ProjectModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def update(self, project: Project) -> Project:
        """Update a project."""
        model = await self._models.get_by_id(project.id)
        if model:
            # Update fields
            model.name = project.name
            model.description = project.description
            model.status = project.status.value
            # We don't change workspace_id or created_at
            await self.session.flush()
        return project

    async def delete(self, project_id: UUID) -> bool:
        """Delete a project."""
        model = await self._models.get_by_id(project_id)
        if model:
            await self._models.delete(model)
            return True
        return False
