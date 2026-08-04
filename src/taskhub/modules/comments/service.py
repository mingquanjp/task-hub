"""Comment service layer handling business logic."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from taskhub.core.exceptions import (
    CommentNotFoundError,
    CommentPermissionDeniedError,
    TaskNotFoundError,
)
from taskhub.modules.comments.entities import Comment
from taskhub.modules.comments.repository import CommentRepository
from taskhub.modules.tasks.repository import TaskRepository
from taskhub.modules.workspaces.entities import WorkspaceRole


class CommentService:
    """Business logic for comments."""

    def __init__(
        self,
        comment_repo: CommentRepository,
        task_repo: TaskRepository,
    ) -> None:
        self.comment_repo = comment_repo
        self.task_repo = task_repo

    async def _verify_task_exists(self, task_id: UUID) -> None:
        """Verify the task exists, else raise 404."""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

    async def create(self, task_id: UUID, author_id: UUID, content: str) -> Comment:
        """Create a new comment."""
        await self._verify_task_exists(task_id)

        comment = Comment(
            id=uuid4(),
            task_id=task_id,
            author_id=author_id,
            content=content,
            created_at=datetime.now(UTC),
        )
        return await self.comment_repo.create(comment)

    async def get(self, task_id: UUID, comment_id: UUID) -> Comment:
        """Get a comment by ID and verify it belongs to the task."""
        await self._verify_task_exists(task_id)

        comment = await self.comment_repo.get_by_id(comment_id)
        if not comment or comment.task_id != task_id:
            raise CommentNotFoundError(f"Comment {comment_id} not found in task {task_id}")

        return comment

    async def list_by_task(
        self, task_id: UUID, *, offset: int = 0, limit: int = 100
    ) -> tuple[Sequence[Comment], int]:
        """List comments for a task."""
        await self._verify_task_exists(task_id)
        return await self.comment_repo.list_by_task(task_id, offset=offset, limit=limit)

    async def update(
        self, task_id: UUID, comment_id: UUID, current_user_id: UUID, content: str
    ) -> Comment:
        """Update an existing comment."""
        comment = await self.get(task_id, comment_id)

        if comment.author_id != current_user_id:
            raise CommentPermissionDeniedError("Only the author can update their comment")

        updated_comment = Comment(
            id=comment.id,
            task_id=comment.task_id,
            author_id=comment.author_id,
            content=content,
            created_at=comment.created_at,
        )

        return await self.comment_repo.update(updated_comment)

    async def delete(
        self,
        task_id: UUID,
        comment_id: UUID,
        current_user_id: UUID,
        workspace_role: WorkspaceRole,
        is_admin: bool = False,
    ) -> None:
        """Delete a comment."""
        comment = await self.get(task_id, comment_id)

        # Policy: Author can delete their own comment. OWNER or ADMIN can delete any comment.
        # EDITOR cannot delete other's comments. VIEWER cannot even reach this endpoint (router blocked).
        can_delete = False

        if comment.author_id == current_user_id:
            can_delete = True
        elif is_admin or workspace_role == WorkspaceRole.OWNER:
            can_delete = True

        if not can_delete:
            raise CommentPermissionDeniedError("You do not have permission to delete this comment")

        await self.comment_repo.delete(comment_id)
