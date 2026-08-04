"""SQLAlchemy implementation of the comment repository."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models.comment import CommentModel
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.comments.entities import Comment
from taskhub.modules.comments.repository import CommentRepository


class SQLAlchemyCommentRepository(CommentRepository):
    """SQLAlchemy implementation of CommentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._models = BaseRepository(session, CommentModel)

    def _to_domain(self, model: CommentModel) -> Comment:
        """Map ORM model to domain entity."""
        return Comment(
            id=model.id,
            task_id=model.task_id,
            author_id=model.author_id,
            content=model.content,
            created_at=model.created_at,
        )

    def _to_model(self, entity: Comment) -> CommentModel:
        """Map domain entity to ORM model."""
        return CommentModel(
            id=entity.id,
            task_id=entity.task_id,
            author_id=entity.author_id,
            content=entity.content,
            created_at=entity.created_at,
        )

    async def create(self, comment: Comment) -> Comment:
        """Create a new comment."""
        model = self._to_model(comment)
        await self._models.add(model)
        return self._to_domain(model)

    async def get_by_id(self, comment_id: UUID) -> Comment | None:
        """Get a comment by its ID."""
        model = await self._models.get_by_id(comment_id)
        if not model:
            return None
        return self._to_domain(model)

    async def update(self, comment: Comment) -> Comment:
        """Update an existing comment."""
        model = await self._models.get_by_id(comment.id)
        if not model:
            raise ValueError(f"Comment {comment.id} not found in database")

        model.content = comment.content
        await self._session.flush()
        return comment

    async def delete(self, comment_id: UUID) -> None:
        """Delete a comment."""
        model = await self._models.get_by_id(comment_id)
        if model:
            await self._models.delete(model)

    async def list_by_task(
        self,
        task_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Comment], int]:
        """List comments for a task with pagination."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if limit > 100:
            raise ValueError("limit must not exceed 100")

        # Build base filter
        filters = [CommentModel.task_id == task_id]

        # Count total
        count_stmt = select(func.count()).select_from(CommentModel).where(*filters)
        total = await self._session.scalar(count_stmt) or 0

        # Fetch page
        stmt = (
            select(CommentModel)
            .where(*filters)
            .order_by(CommentModel.created_at.asc(), CommentModel.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self._session.scalars(stmt)
        comments = [self._to_domain(m) for m in result.all()]

        return comments, total
