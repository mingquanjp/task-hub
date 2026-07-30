"""Domain entities for labels."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Label:
    """A project-scoped label independent of HTTP and persistence concerns."""

    id: UUID
    project_id: UUID
    name: str
    color: str
