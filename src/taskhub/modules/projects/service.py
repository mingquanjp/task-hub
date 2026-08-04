"""Business logic for projects."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from taskhub.core.exceptions import (
    ProjectAlreadyArchivedError,
    ProjectNotFoundError,
)
from taskhub.modules.projects.entities import Project, ProjectStatus
from taskhub.modules.projects.repository import ProjectRepository


class ProjectService:
    """Service handling project business logic."""

    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    async def create(self, workspace_id: UUID, name: str, description: str | None) -> Project:
        """Create a new project in a workspace."""
        project = Project(
            id=uuid4(),
            workspace_id=workspace_id,
            name=name,
            description=description,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )
        return await self.project_repo.create(project)

    async def get(self, project_id: UUID) -> Project:
        """Get a project by ID."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return project

    async def list_by_workspace(self, workspace_id: UUID) -> list[Project]:
        """List all projects for a workspace."""
        return await self.project_repo.list_by_workspace(workspace_id)

    async def update(
        self,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        # Explicitly use a flag to differentiate "not sent" from "sent as None"
        description_is_set: bool = False,
    ) -> Project:
        """Update a project."""
        project = await self.get(project_id)

        if name is not None:
            project.name = name

        if description_is_set:
            project.description = description

        return await self.project_repo.update(project)

    async def archive(self, project_id: UUID) -> Project:
        """Archive a project."""
        project = await self.get(project_id)

        if project.status == ProjectStatus.ARCHIVED:
            raise ProjectAlreadyArchivedError("Project is already archived")

        project.status = ProjectStatus.ARCHIVED
        return await self.project_repo.update(project)

    async def delete(self, project_id: UUID) -> None:
        """Delete a project."""
        project = await self.get(project_id)
        if project.status != ProjectStatus.ARCHIVED:
            # Tuỳ theo yêu cầu khác, chọn policy đơn giản: PATCH/DELETE
            # project archived phải có behavior rõ ràng.
            # Do we allow deleting archived projects?
            # A simple policy is to allow it, so we don't enforce active state to delete it.
            # We'll leave it as direct delete for now.
            pass

        deleted = await self.project_repo.delete(project_id)
        if not deleted:
            raise ProjectNotFoundError(f"Project {project_id} not found")
