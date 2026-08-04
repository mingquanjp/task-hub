"""SQLAlchemy ORM model for comments."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.task import TaskModel
    from taskhub.infrastructure.database.models.user import UserModel


class CommentModel(Base):
    """ORM representation of the comments table."""

    __tablename__ = "comments"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    task: Mapped["TaskModel"] = relationship(back_populates="comments")
    author: Mapped["UserModel"] = relationship(back_populates="comments")
