"""Unit tests for the workspace application service."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from taskhub.core.exceptions import (
    InvalidWorkspaceRoleError,
    PermissionDeniedError,
    ResourceNotFoundError,
    WorkspaceOwnerRemovalError,
)
from taskhub.modules.auth.entities import User, UserRole
from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole
from taskhub.modules.workspaces.service import WorkspaceService


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self.workspaces: dict[UUID, Workspace] = {}

    async def create(self, workspace: Workspace) -> Workspace:
        self.workspaces[workspace.id] = workspace
        return workspace

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        return self.workspaces.get(workspace_id)

    async def get_by_id_with_members(  # type: ignore
        self,
        workspace_id: UUID,
    ) -> tuple[Workspace, list[WorkspaceMember]] | None:
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return None
        # This will be injected by the test runner for the sake of simplicity
        # Real repo joins, but here we can just pass an empty list and mock members directly
        # on the fake later if needed
        # Wait, a better way is to pass the member repo to this fake, or just store members here.
        # But for test isolation, let's just make it return what we set.
        pass


class FakeWorkspaceMemberRepository:
    def __init__(self) -> None:
        self.members: dict[tuple[UUID, UUID], WorkspaceMember] = {}

    async def create(self, member: WorkspaceMember) -> WorkspaceMember:
        if (member.workspace_id, member.user_id) in self.members:
            raise Exception("IntegrityError")  # Simulating SQLAlchemy IntegrityError
        self.members[(member.workspace_id, member.user_id)] = member
        return member

    async def get(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        return self.members.get((workspace_id, user_id))

    async def list_by_workspace(self, workspace_id: UUID) -> list[WorkspaceMember]:
        return [m for m in self.members.values() if m.workspace_id == workspace_id]

    async def delete(self, workspace_id: UUID, user_id: UUID) -> bool:
        if (workspace_id, user_id) in self.members:
            del self.members[(workspace_id, user_id)]
            return True
        return False


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    # other methods omitted for brevity


@pytest.fixture
def fakes() -> tuple[FakeWorkspaceRepository, FakeWorkspaceMemberRepository, FakeUserRepository]:
    return FakeWorkspaceRepository(), FakeWorkspaceMemberRepository(), FakeUserRepository()


@pytest.fixture
def service(fakes: tuple) -> WorkspaceService:  # type: ignore
    workspace_repo, member_repo, user_repo = fakes

    # Monkey-patch get_by_id_with_members to return members from member_repo
    async def get_by_id_with_members(
        workspace_id: UUID,
    ) -> tuple[Workspace, list[WorkspaceMember]] | None:
        workspace = workspace_repo.workspaces.get(workspace_id)
        if not workspace:
            return None
        members = [m for m in member_repo.members.values() if m.workspace_id == workspace_id]
        return workspace, members

    workspace_repo.get_by_id_with_members = get_by_id_with_members
    return WorkspaceService(workspace_repo, member_repo, user_repo)


@pytest.fixture
def actor() -> User:
    return User(
        id=uuid4(),
        email="actor@example.com",
        full_name="Actor",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_create_workspace(
    service: WorkspaceService,
    fakes: tuple[FakeWorkspaceRepository, FakeWorkspaceMemberRepository, FakeUserRepository],
    actor: User,
) -> None:
    workspace_repo, member_repo, _ = fakes

    workspace = await service.create(actor, "New Workspace")
    assert workspace.name == "New Workspace"
    assert workspace.owner_id == actor.id

    assert workspace.id in workspace_repo.workspaces

    member = await member_repo.get(workspace.id, actor.id)
    assert member is not None
    assert member.role == WorkspaceRole.OWNER


@pytest.mark.asyncio
async def test_get_workspace_as_member(
    service: WorkspaceService,
    fakes: tuple,  # type: ignore
    actor: User,
) -> None:
    workspace = await service.create(actor, "My Workspace")

    details = await service.get(actor, workspace.id)
    assert details.workspace.id == workspace.id
    assert len(details.members) == 1
    assert details.members[0].role == WorkspaceRole.OWNER


@pytest.mark.asyncio
async def test_get_workspace_as_non_member_denied(
    service: WorkspaceService,
) -> None:
    owner = User(
        id=uuid4(),
        email="o@o.com",
        full_name="o",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    workspace = await service.create(owner, "My Workspace")

    non_member = User(
        id=uuid4(),
        email="n@n.com",
        full_name="n",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )

    with pytest.raises(PermissionDeniedError):
        await service.get(non_member, workspace.id)


@pytest.mark.asyncio
async def test_get_workspace_as_admin_allowed(
    service: WorkspaceService,
) -> None:
    owner = User(
        id=uuid4(),
        email="o@o.com",
        full_name="o",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    workspace = await service.create(owner, "My Workspace")

    admin = User(
        id=uuid4(),
        email="a@a.com",
        full_name="a",
        role=UserRole.ADMIN,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    details = await service.get(admin, workspace.id)
    assert details.workspace.id == workspace.id


@pytest.mark.asyncio
async def test_invite_member(
    service: WorkspaceService,
    fakes: tuple,  # type: ignore
    actor: User,
) -> None:
    _, _, user_repo = fakes
    workspace = await service.create(actor, "My Workspace")

    target_user = User(
        id=uuid4(),
        email="t@t.com",
        full_name="t",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    user_repo.users[target_user.id] = target_user

    member = await service.invite_member(actor, workspace.id, target_user.id, WorkspaceRole.EDITOR)
    assert member.role == WorkspaceRole.EDITOR


@pytest.mark.asyncio
async def test_invite_member_prevent_owner_role(
    service: WorkspaceService,
    fakes: tuple,  # type: ignore
    actor: User,
) -> None:
    _, _, user_repo = fakes
    workspace = await service.create(actor, "My Workspace")

    target_user = User(
        id=uuid4(),
        email="t@t.com",
        full_name="t",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    user_repo.users[target_user.id] = target_user

    with pytest.raises(InvalidWorkspaceRoleError):
        await service.invite_member(actor, workspace.id, target_user.id, WorkspaceRole.OWNER)


@pytest.mark.asyncio
async def test_remove_member(
    service: WorkspaceService,
    fakes: tuple,  # type: ignore
    actor: User,
) -> None:
    _, _, user_repo = fakes
    workspace = await service.create(actor, "My Workspace")

    target_user = User(
        id=uuid4(),
        email="t@t.com",
        full_name="t",
        role=UserRole.MEMBER,
        is_active=True,
        hashed_password="hash",
        created_at=datetime.now(UTC),
    )
    user_repo.users[target_user.id] = target_user

    await service.invite_member(actor, workspace.id, target_user.id, WorkspaceRole.VIEWER)

    await service.remove_member(actor, workspace.id, target_user.id)

    with pytest.raises(ResourceNotFoundError):
        await service.remove_member(actor, workspace.id, target_user.id)


@pytest.mark.asyncio
async def test_remove_owner_denied(
    service: WorkspaceService,
    fakes: tuple,  # type: ignore
    actor: User,
) -> None:
    workspace = await service.create(actor, "My Workspace")

    with pytest.raises(WorkspaceOwnerRemovalError):
        await service.remove_member(actor, workspace.id, actor.id)
