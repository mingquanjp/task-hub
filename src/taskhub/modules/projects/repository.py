"""Repository contract for projects."""

from typing import Protocol
from uuid import UUID

from taskhub.modules.projects.entities import Project


class ProjectRepository(Protocol):
    """Abstract persistence contract for projects."""

    async def create(self, project: Project) -> Project:
        """Persist a new project."""
        ...

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get a project by its ID."""
        ...

    async def list_by_workspace(self, workspace_id: UUID) -> list[Project]:
        """List all projects in a workspace."""
        ...

    async def update(self, project: Project) -> Project:
        """Update an existing project."""
        ...

    async def delete(self, project_id: UUID) -> bool:
        """Delete a project. Returns True if deleted, False if not found."""
        ...
