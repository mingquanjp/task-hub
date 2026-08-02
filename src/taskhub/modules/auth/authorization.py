"""Role-based access control and authorization boundaries."""

from enum import StrEnum

from taskhub.modules.auth.entities import UserRole
from taskhub.modules.workspaces.entities import WorkspaceRole


class ResourceAction(StrEnum):
    """Actions that can be performed on resources."""

    VIEW = "VIEW"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MANAGE_MEMBERS = "MANAGE_MEMBERS"


def can_perform_action(
    system_role: UserRole,
    workspace_role: WorkspaceRole | None,
    action: ResourceAction,
) -> bool:
    """Evaluate whether the given roles allow the requested action."""
    if system_role == UserRole.ADMIN:
        return True

    if workspace_role is None:
        return False

    if workspace_role == WorkspaceRole.OWNER:
        return True

    if workspace_role == WorkspaceRole.EDITOR:
        return action in (ResourceAction.VIEW, ResourceAction.CREATE, ResourceAction.UPDATE)

    if workspace_role == WorkspaceRole.VIEWER:
        return action == ResourceAction.VIEW

    return False


def require_workspace_member() -> None:
    """Placeholder for dependency to require a user is a member of the requested workspace.

    Will be implemented in Task 4 when Workspace persistence exists.
    """
    raise NotImplementedError("Workspace membership is not yet implemented")


def require_workspace_role(action: ResourceAction) -> None:
    """Placeholder for dependency to require a specific role in the requested workspace.

    Will be implemented in Task 4 when Workspace persistence exists.
    """
    raise NotImplementedError("Workspace roles are not yet implemented")
