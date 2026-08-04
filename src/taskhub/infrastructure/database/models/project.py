"""SQLAlchemy model for TaskHub projects."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.label import LabelModel
    from taskhub.infrastructure.database.models.task import TaskModel
    from taskhub.infrastructure.database.models.workspace import WorkspaceModel


class ProjectModel(Base):
    """Project persistence model containing tasks and labels."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workspace: Mapped[WorkspaceModel] = relationship(
        back_populates="projects",
    )
    labels: Mapped[list[LabelModel]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[list[TaskModel]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
