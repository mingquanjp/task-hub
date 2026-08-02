"""SQLAlchemy implementation of workspace repositories."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskhub.infrastructure.database.models.workspace import WorkspaceModel
from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember
from taskhub.modules.workspaces.repository import WorkspaceMembershipConflictError


def _to_workspace_domain(model: WorkspaceModel) -> Workspace:
    return Workspace(
        id=model.id,
        name=model.name,
        owner_id=model.owner_id,
        created_at=model.created_at,
    )


def _to_member_domain(model: WorkspaceMemberModel) -> WorkspaceMember:
    return WorkspaceMember(
        workspace_id=model.workspace_id,
        user_id=model.user_id,
        role=model.role,
        created_at=model.created_at,
    )


class SQLAlchemyWorkspaceRepository:
    """SQLAlchemy implementation of WorkspaceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workspace: Workspace) -> Workspace:
        """Persist a new workspace."""
        model = WorkspaceModel(
            id=workspace.id,
            name=workspace.name,
            owner_id=workspace.owner_id,
            created_at=workspace.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_workspace_domain(model)

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        """Retrieve a workspace by its unique identifier."""
        model = await self._session.get(WorkspaceModel, workspace_id)
        if model is None:
            return None
        return _to_workspace_domain(model)

    async def get_by_id_with_members(
        self,
        workspace_id: UUID,
    ) -> tuple[Workspace, list[WorkspaceMember]] | None:
        """Retrieve a workspace along with all its members."""
        stmt = (
            select(WorkspaceModel)
            .options(selectinload(WorkspaceModel.members))
            .where(WorkspaceModel.id == workspace_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        workspace = _to_workspace_domain(model)
        members = [_to_member_domain(member) for member in model.members]
        return workspace, members


class SQLAlchemyWorkspaceMemberRepository:
    """SQLAlchemy implementation of WorkspaceMemberRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, member: WorkspaceMember) -> WorkspaceMember:
        """Persist a new workspace membership."""
        model = WorkspaceMemberModel(
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            role=member.role,
            created_at=member.created_at,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Re-raise as a distinct persistence exception
            raise WorkspaceMembershipConflictError("Membership conflict in database") from exc

        return _to_member_domain(model)

    async def get(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        """Retrieve a specific user's membership in a workspace."""
        stmt = select(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id,
            WorkspaceMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None
        return _to_member_domain(model)

    async def list_by_workspace(self, workspace_id: UUID) -> list[WorkspaceMember]:
        """List all members of a workspace."""
        stmt = select(WorkspaceMemberModel).where(WorkspaceMemberModel.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_member_domain(model) for model in models]

    async def delete(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Remove a user's membership from a workspace."""
        stmt = delete(WorkspaceMemberModel).where(
            WorkspaceMemberModel.workspace_id == workspace_id,
            WorkspaceMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        # Explicitly cast to CursorResult for mypy
        from typing import Any, cast

        cursor = cast(CursorResult[Any], result)
        return cursor.rowcount > 0
