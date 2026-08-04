"""SQLAlchemy model for TaskHub tasks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.comment import CommentModel
    from taskhub.infrastructure.database.models.label import LabelModel
    from taskhub.infrastructure.database.models.project import ProjectModel
    from taskhub.infrastructure.database.models.user import UserModel


class TaskModel(Base):
    """Task persistence model."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_priority", "project_id", "priority"),
        Index("ix_tasks_project_assignee", "project_id", "assignee_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped[ProjectModel] = relationship(back_populates="tasks")
    assignee: Mapped[UserModel | None] = relationship(
        foreign_keys=[assignee_id], back_populates="assigned_tasks"
    )
    creator: Mapped[UserModel] = relationship(
        foreign_keys=[created_by], back_populates="created_tasks"
    )
    comments: Mapped[list[CommentModel]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    labels: Mapped[list[LabelModel]] = relationship(secondary="task_labels", back_populates="tasks")
