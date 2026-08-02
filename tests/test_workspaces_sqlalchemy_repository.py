"""Database tests for workspace repositories."""

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from taskhub.infrastructure.database.models.user import UserModel
from taskhub.infrastructure.database.session import Database
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole
from taskhub.modules.workspaces.repository import WorkspaceMembershipConflictError
from taskhub.modules.workspaces.sqlalchemy_repository import (
    SQLAlchemyWorkspaceMemberRepository,
    SQLAlchemyWorkspaceRepository,
)


@pytest_asyncio.fixture
async def setup_users(database_url: str) -> AsyncGenerator[tuple[UUID, UUID], None]:
    database = Database(database_url)
    owner_id = uuid4()
    member_id = uuid4()
    async with database.session_factory() as session:
        user1 = UserModel(
            id=owner_id, email="owner@test.com", full_name="Owner", hashed_password="hash"
        )
        user2 = UserModel(
            id=member_id, email="member@test.com", full_name="Member", hashed_password="hash"
        )
        session.add_all([user1, user2])
        await session.commit()

    yield owner_id, member_id

    await database.dispose()


@pytest.mark.asyncio
async def test_workspace_repositories(database_url: str, setup_users: tuple[UUID, UUID]) -> None:
    owner_id, member_id = setup_users
    database = Database(database_url)
    workspace_id = uuid4()

    async with database.session_factory() as session:
        workspace_repo = SQLAlchemyWorkspaceRepository(session)
        member_repo = SQLAlchemyWorkspaceMemberRepository(session)

        # 1. Create Workspace
        import datetime

        now = datetime.datetime.now(datetime.UTC)
        new_workspace = Workspace(
            id=workspace_id,
            name="Test Repositories",
            owner_id=owner_id,
            created_at=now,
        )
        workspace = await workspace_repo.create(new_workspace)
        assert workspace.id == workspace_id

        # 2. Create Owner Member
        owner_member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
            created_at=now,
        )
        await member_repo.create(owner_member)

        # 3. Create Another Member
        viewer_member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=member_id,
            role=WorkspaceRole.VIEWER,
            created_at=now,
        )
        await member_repo.create(viewer_member)

        # Commit to save to DB so we can query in a new session (or flush if same session)
        await session.commit()

    async with database.session_factory() as session:
        workspace_repo = SQLAlchemyWorkspaceRepository(session)
        member_repo = SQLAlchemyWorkspaceMemberRepository(session)

        # 4. get_by_id_with_members (Eager loading)
        result = await workspace_repo.get_by_id_with_members(workspace_id)
        assert result is not None
        fetched_workspace, fetched_members = result
        assert fetched_workspace.name == "Test Repositories"
        assert len(fetched_members) == 2

        # 5. duplicate member should raise IntegrityError
        dup_member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=member_id,
            role=WorkspaceRole.EDITOR,
            created_at=now,
        )
        with pytest.raises(WorkspaceMembershipConflictError):
            await member_repo.create(dup_member)

        await session.rollback()

    async with database.session_factory() as session:
        member_repo = SQLAlchemyWorkspaceMemberRepository(session)

        # 6. Delete member
        deleted = await member_repo.delete(workspace_id, member_id)
        assert deleted is True

        not_found = await member_repo.get(workspace_id, member_id)
        assert not_found is None

        await session.commit()

    await database.dispose()


@pytest.mark.asyncio
async def test_workspace_cascade_deletes(database_url: str, setup_users: tuple[UUID, UUID]) -> None:
    owner_id, member_id = setup_users
    database = Database(database_url)
    workspace_id = uuid4()

    # Create workspace and member
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    async with database.session_factory() as session:
        workspace_repo = SQLAlchemyWorkspaceRepository(session)
        member_repo = SQLAlchemyWorkspaceMemberRepository(session)

        ws = Workspace(id=workspace_id, name="Cascade Test", owner_id=owner_id, created_at=now)
        await workspace_repo.create(ws)

        mem = WorkspaceMember(
            workspace_id=workspace_id, user_id=member_id, role=WorkspaceRole.VIEWER, created_at=now
        )
        await member_repo.create(mem)
        await session.commit()

    # Delete workspace and assert member is cascaded
    async with database.session_factory() as session:
        # We don't have a delete workspace in repo yet,
        # so we execute raw SQL to test DB level cascade
        from sqlalchemy import delete

        from taskhub.infrastructure.database.models.workspace import WorkspaceModel

        stmt = delete(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
        await session.execute(stmt)
        await session.commit()

    async with database.session_factory() as session:
        member_repo = SQLAlchemyWorkspaceMemberRepository(session)
        fetched_mem = await member_repo.get(workspace_id, member_id)
        assert fetched_mem is None, "Membership should be cascaded when workspace is deleted"

    await database.dispose()
