"""Repository contracts for the workspace domain."""

from typing import Protocol
from uuid import UUID

from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember


class WorkspaceMembershipConflictError(Exception):
    """Raised by the repository when a database membership conflict occurs."""

    pass


class WorkspaceRepository(Protocol):
    """Data access contract for Workspace entities."""

    async def create(self, workspace: Workspace) -> Workspace:
        """Persist a new workspace."""
        ...

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        """Retrieve a workspace by its unique identifier."""
        ...

    async def get_by_id_with_members(
        self,
        workspace_id: UUID,
    ) -> tuple[Workspace, list[WorkspaceMember]] | None:
        """Retrieve a workspace along with all its members."""
        ...


class WorkspaceMemberRepository(Protocol):
    """Data access contract for WorkspaceMember entities."""

    async def create(self, member: WorkspaceMember) -> WorkspaceMember:
        """Persist a new workspace membership."""
        ...

    async def get(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        """Retrieve a specific user's membership in a workspace."""
        ...

    async def list_by_workspace(
        self,
        workspace_id: UUID,
    ) -> list[WorkspaceMember]:
        """List all members of a workspace."""
        ...

    async def delete(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Remove a user's membership from a workspace.

        Returns True if the membership was deleted, False if it did not exist.
        """
        ...
