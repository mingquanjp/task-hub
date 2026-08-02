"""Tests for pure Python authorization policies and dependencies."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from taskhub.core.exceptions import PermissionDeniedError
from taskhub.modules.auth.authorization import ResourceAction, WorkspaceRole, can_perform_action
from taskhub.modules.auth.dependencies import require_admin
from taskhub.modules.auth.entities import User, UserRole


@pytest.fixture
def active_user() -> User:
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="User",
        hashed_password="hash",
        role=UserRole.MEMBER,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def test_can_perform_action_admin_can_do_anything() -> None:
    assert can_perform_action(UserRole.ADMIN, None, ResourceAction.DELETE) is True
    assert (
        can_perform_action(UserRole.ADMIN, WorkspaceRole.VIEWER, ResourceAction.MANAGE_MEMBERS)
        is True
    )


def test_can_perform_action_no_workspace_role_cannot_do_anything() -> None:
    assert can_perform_action(UserRole.MEMBER, None, ResourceAction.VIEW) is False


def test_can_perform_action_owner_can_do_anything() -> None:
    for action in ResourceAction:
        assert can_perform_action(UserRole.MEMBER, WorkspaceRole.OWNER, action) is True


def test_can_perform_action_editor_capabilities() -> None:
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.EDITOR, ResourceAction.VIEW) is True
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.EDITOR, ResourceAction.CREATE) is True
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.EDITOR, ResourceAction.UPDATE) is True
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.EDITOR, ResourceAction.DELETE) is False
    assert (
        can_perform_action(UserRole.MEMBER, WorkspaceRole.EDITOR, ResourceAction.MANAGE_MEMBERS)
        is False
    )


def test_can_perform_action_viewer_capabilities() -> None:
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.VIEWER, ResourceAction.VIEW) is True
    assert can_perform_action(UserRole.MEMBER, WorkspaceRole.VIEWER, ResourceAction.CREATE) is False


def test_require_admin_success(active_user: User) -> None:
    from dataclasses import replace

    admin = replace(active_user, role=UserRole.ADMIN)
    assert require_admin(admin) == admin


def test_require_admin_fails_for_member(active_user: User) -> None:
    from dataclasses import replace

    member = replace(active_user, role=UserRole.MEMBER)
    with pytest.raises(PermissionDeniedError):
        require_admin(member)


def test_workspace_placeholders_fail_closed() -> None:
    from taskhub.modules.auth.authorization import require_workspace_member, require_workspace_role

    with pytest.raises(NotImplementedError):
        require_workspace_member()

    with pytest.raises(NotImplementedError):
        require_workspace_role(ResourceAction.VIEW)
