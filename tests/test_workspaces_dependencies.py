"""Unit tests for Workspace dependencies."""

from uuid import UUID, uuid4

import pytest

from taskhub.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.workspaces.dependencies import (
    require_workspace_member,
    require_workspace_role,
)
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole


class FakeWorkspaceRepositoryForDeps:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.owner_id = uuid4()
        self.editor_id = uuid4()
        self.viewer_id = uuid4()

    async def get_by_id_with_members(
        self, workspace_id: UUID
    ) -> tuple[Workspace, list[WorkspaceMember]] | None:
        if workspace_id != self.workspace_id:
            return None

        workspace = Workspace(
            id=workspace_id,
            name="Test",
            owner_id=self.owner_id,
            created_at=None,  # type: ignore
        )
        members = [
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=self.owner_id,
                role=WorkspaceRole.OWNER,
                created_at=None,  # type: ignore
            ),
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=self.editor_id,
                role=WorkspaceRole.EDITOR,
                created_at=None,  # type: ignore
            ),
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=self.viewer_id,
                role=WorkspaceRole.VIEWER,
                created_at=None,  # type: ignore
            ),
        ]
        return workspace, members


@pytest.fixture
def fake_repo() -> FakeWorkspaceRepositoryForDeps:
    return FakeWorkspaceRepositoryForDeps()


def make_user(user_id: UUID, role: UserRole = UserRole.MEMBER) -> User:
    return User(
        id=user_id,
        email="test@test.com",
        full_name="Test",
        role=role,
        is_active=True,
        hashed_password="hash",
        created_at=None,  # type: ignore
    )


@pytest.mark.asyncio
async def test_require_workspace_member_admin_bypass(
    fake_repo: FakeWorkspaceRepositoryForDeps,
) -> None:
    admin_user = make_user(uuid4(), UserRole.ADMIN)
    # Even if they are not in the workspace, ADMIN should be allowed
    user = await require_workspace_member(fake_repo.workspace_id, admin_user, fake_repo)  # type: ignore
    assert user == admin_user


@pytest.mark.asyncio
async def test_require_workspace_member_allowed(
    fake_repo: FakeWorkspaceRepositoryForDeps,
) -> None:
    member_user = make_user(fake_repo.editor_id)
    user = await require_workspace_member(fake_repo.workspace_id, member_user, fake_repo)  # type: ignore
    assert user == member_user


@pytest.mark.asyncio
async def test_require_workspace_member_denied(
    fake_repo: FakeWorkspaceRepositoryForDeps,
) -> None:
    non_member = make_user(uuid4())
    with pytest.raises(PermissionDeniedError):
        await require_workspace_member(fake_repo.workspace_id, non_member, fake_repo)  # type: ignore


@pytest.mark.asyncio
async def test_require_workspace_member_not_found(
    fake_repo: FakeWorkspaceRepositoryForDeps,
) -> None:
    non_member = make_user(uuid4())
    with pytest.raises(ResourceNotFoundError):
        await require_workspace_member(uuid4(), non_member, fake_repo)  # type: ignore


@pytest.mark.asyncio
async def test_require_workspace_role_owner(
    fake_repo: FakeWorkspaceRepositoryForDeps,
) -> None:
    dep = require_workspace_role(WorkspaceRole.OWNER)

    owner = make_user(fake_repo.owner_id)
    user = await dep(fake_repo.workspace_id, owner, fake_repo)  # type: ignore
    assert user == owner

    # Admin bypasses
    admin = make_user(uuid4(), UserRole.ADMIN)
    user = await dep(fake_repo.workspace_id, admin, fake_repo)  # type: ignore
    assert user == admin

    # Editor denied
    editor = make_user(fake_repo.editor_id)
    with pytest.raises(PermissionDeniedError):
        await dep(fake_repo.workspace_id, editor, fake_repo)  # type: ignore

    # Non member denied
    non_member = make_user(uuid4())
    with pytest.raises(PermissionDeniedError):
        await dep(fake_repo.workspace_id, non_member, fake_repo)  # type: ignore
