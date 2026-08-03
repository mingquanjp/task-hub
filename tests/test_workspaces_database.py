"""Database integration tests for workspaces and memberships."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from taskhub.infrastructure.database.models.user import UserModel
from taskhub.infrastructure.database.models.workspace import WorkspaceModel
from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel
from taskhub.modules.workspaces.entities import WorkspaceRole


@pytest.mark.asyncio
async def test_workspace_and_member_persistence(database_url: str) -> None:
    from taskhub.infrastructure.database.session import Database

    database = Database(database_url)
    factory = database.session_factory

    # 1. Create a user
    owner_id = uuid4()
    user2_id = uuid4()
    async with factory() as session:
        user1 = UserModel(
            id=owner_id,
            email="owner@example.com",
            full_name="Owner",
            hashed_password="hash",
        )
        user2 = UserModel(
            id=user2_id,
            email="member@example.com",
            full_name="Member",
            hashed_password="hash",
        )
        session.add_all([user1, user2])
        await session.commit()

    # 2. Create workspace and members
    workspace_id = uuid4()
    async with factory() as session:
        workspace = WorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=owner_id,
        )
        session.add(workspace)
        await session.commit()

        member1 = WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        member2 = WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=user2_id,
            role=WorkspaceRole.VIEWER,
        )
        session.add_all([member1, member2])
        await session.commit()

    # 3. Test duplicates are rejected (Composite PK)
    async with factory() as session:
        duplicate = WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=owner_id,
            role=WorkspaceRole.EDITOR,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 4. Test RESTRICT on owner
    async with factory() as session:
        owner = await session.get(UserModel, owner_id)
        assert owner is not None
        await session.delete(owner)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 5. Test CASCADE on workspace deletion
    async with factory() as session:
        workspace_obj = await session.get(WorkspaceModel, workspace_id)
        assert workspace_obj is not None
        await session.delete(workspace_obj)
        await session.commit()

        # Verify members are cascade deleted
        result = await session.execute(
            select(WorkspaceMemberModel).where(WorkspaceMemberModel.workspace_id == workspace_id)
        )
        assert len(result.scalars().all()) == 0
