"""SQLAlchemy persistence model for labels."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.project import ProjectModel
    from taskhub.infrastructure.database.models.task import TaskModel


class LabelModel(Base):
    """Database representation of a label belonging to one project."""

    __tablename__ = "labels"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped[ProjectModel] = relationship(back_populates="labels")
    tasks: Mapped[list[TaskModel]] = relationship(secondary="task_labels", back_populates="labels")
