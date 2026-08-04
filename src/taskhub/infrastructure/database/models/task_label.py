"""SQLAlchemy ORM model for task labels many-to-many relationship."""

from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from taskhub.infrastructure.database.base import Base


class TaskLabelModel(Base):
    """Association table between tasks and labels."""

    __tablename__ = "task_labels"

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[UUID] = mapped_column(
        ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True
    )
