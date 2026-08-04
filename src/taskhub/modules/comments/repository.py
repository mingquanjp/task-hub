"""Comment repository interface."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from taskhub.modules.comments.entities import Comment


class CommentRepository(Protocol):
    """Data access contract for comments."""

    async def create(self, comment: Comment) -> Comment:
        """Create a new comment."""
        ...

    async def get_by_id(self, comment_id: UUID) -> Comment | None:
        """Get a comment by its ID."""
        ...

    async def list_by_task(
        self, task_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> tuple[Sequence[Comment], int]:
        """
        List comments for a task.

        Returns:
            A tuple of (comments, total_count).
        """
        ...

    async def update(self, comment: Comment) -> Comment:
        """Update an existing comment."""
        ...

    async def delete(self, comment_id: UUID) -> None:
        """Delete a comment."""
        ...
