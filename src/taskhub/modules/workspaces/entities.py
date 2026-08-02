"""Domain entities and roles for workspaces."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class WorkspaceRole(StrEnum):
    """Resource-level roles for workspace members."""

    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


@dataclass(frozen=True, slots=True)
class Workspace:
    """A workspace container for projects and members."""

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WorkspaceMember:
    """A user's membership and role in a workspace."""

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    created_at: datetime
