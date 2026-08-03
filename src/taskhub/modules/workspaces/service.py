"""Application service for the workspace domain."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from taskhub.core.exceptions import (
    InvalidWorkspaceRoleError,
    PermissionDeniedError,
    ResourceNotFoundError,
    WorkspaceMemberAlreadyExistsError,
    WorkspaceOwnerRemovalError,
)
from taskhub.modules.auth.authorization import ResourceAction, can_perform_action
from taskhub.modules.auth.entities import User
from taskhub.modules.auth.repository import UserRepository
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole
from taskhub.modules.workspaces.repository import (
    WorkspaceMemberRepository,
    WorkspaceMembershipConflictError,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class WorkspaceDetails:
    """Detailed view of a workspace and its members."""

    workspace: Workspace
    members: tuple[WorkspaceMember, ...]


class WorkspaceService:
    """Business logic for workspaces."""

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
        user_repo: UserRepository,
    ) -> None:
        self._workspace_repo = workspace_repo
        self._member_repo = member_repo
        self._user_repo = user_repo

    async def create(
        self,
        actor: User,
        name: str,
    ) -> Workspace:
        """Create a new workspace and make the actor its owner."""
        # Validate name
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Workspace name cannot be empty")

        now = datetime.now(UTC)
        workspace = Workspace(
            id=uuid4(),
            name=clean_name,
            owner_id=actor.id,
            created_at=now,
        )
        workspace = await self._workspace_repo.create(workspace)

        owner_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=actor.id,
            role=WorkspaceRole.OWNER,
            created_at=now,
        )
        await self._member_repo.create(owner_member)

        return workspace

    async def get(
        self,
        actor: User,
        workspace_id: UUID,
    ) -> WorkspaceDetails:
        """Retrieve a workspace and its members if authorized."""
        result = await self._workspace_repo.get_by_id_with_members(workspace_id)
        if result is None:
            raise ResourceNotFoundError("Workspace not found")

        workspace, members = result

        # Check authorization
        member_role = next((m.role for m in members if m.user_id == actor.id), None)
        if not can_perform_action(actor.role, member_role, ResourceAction.VIEW):
            raise PermissionDeniedError("Cannot view workspace")

        return WorkspaceDetails(
            workspace=workspace,
            members=tuple(members),
        )

    async def invite_member(
        self,
        actor: User,
        workspace_id: UUID,
        target_user_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        """Add a new member to the workspace."""
        if role == WorkspaceRole.OWNER:
            raise InvalidWorkspaceRoleError("Cannot invite a new OWNER")

        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found")

        # Check authorization
        actor_member = await self._member_repo.get(workspace_id, actor.id)
        actor_role = actor_member.role if actor_member else None
        if not can_perform_action(actor.role, actor_role, ResourceAction.MANAGE_MEMBERS):
            raise PermissionDeniedError("Cannot manage workspace members")

        # Verify target user exists
        target_user = await self._user_repo.get_by_id(target_user_id)
        if target_user is None:
            raise ResourceNotFoundError("Target user not found")

        # Verify target is not already a member
        existing_member = await self._member_repo.get(workspace_id, target_user_id)
        if existing_member is not None:
            raise WorkspaceMemberAlreadyExistsError("User is already a member")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=role,
            created_at=datetime.now(UTC),
        )

        # We catch the specific persistence error from the repository and map it.
        try:
            return await self._member_repo.create(member)
        except WorkspaceMembershipConflictError as exc:
            raise WorkspaceMemberAlreadyExistsError("User is already a member") from exc

    async def remove_member(
        self,
        actor: User,
        workspace_id: UUID,
        target_user_id: UUID,
    ) -> None:
        """Remove a member from the workspace."""
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace not found")

        # Check authorization
        actor_member = await self._member_repo.get(workspace_id, actor.id)
        actor_role = actor_member.role if actor_member else None
        if not can_perform_action(actor.role, actor_role, ResourceAction.MANAGE_MEMBERS):
            raise PermissionDeniedError("Cannot manage workspace members")

        # Cannot remove the workspace owner
        if target_user_id == workspace.owner_id:
            raise WorkspaceOwnerRemovalError("Cannot remove the workspace owner")

        target_member = await self._member_repo.get(workspace_id, target_user_id)
        if target_member is None:
            raise ResourceNotFoundError("Target user is not a member of this workspace")

        await self._member_repo.delete(workspace_id, target_user_id)
