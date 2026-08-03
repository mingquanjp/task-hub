"""Domain entities for projects."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ProjectStatus(StrEnum):
    """Lifecycle status of a project."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass
class Project:
    """A project containing tasks and labels, scoped to a workspace."""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
