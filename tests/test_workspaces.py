"""Unit tests for workspace domain entities and roles."""

from datetime import UTC, datetime
from uuid import uuid4

from taskhub.modules.workspaces.entities import Workspace, WorkspaceMember, WorkspaceRole


def test_workspace_role_enum_values() -> None:
    assert WorkspaceRole.OWNER == "OWNER"
    assert WorkspaceRole.EDITOR == "EDITOR"
    assert WorkspaceRole.VIEWER == "VIEWER"


def test_workspace_entity_instantiation() -> None:
    workspace = Workspace(
        id=uuid4(),
        name="My Workspace",
        owner_id=uuid4(),
        created_at=datetime.now(UTC),
    )
    assert workspace.name == "My Workspace"
    assert hasattr(workspace, "id")
    assert hasattr(workspace, "owner_id")
    assert hasattr(workspace, "created_at")


def test_workspace_member_entity_instantiation() -> None:
    member = WorkspaceMember(
        workspace_id=uuid4(),
        user_id=uuid4(),
        role=WorkspaceRole.EDITOR,
        created_at=datetime.now(UTC),
    )
    assert member.role == WorkspaceRole.EDITOR
    assert hasattr(member, "workspace_id")
    assert hasattr(member, "user_id")
    assert hasattr(member, "created_at")
