"""Comment domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Comment:
    """Domain representation of a task comment."""

    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
