"""SQLAlchemy model for TaskHub workspaces."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.user import UserModel
    from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel


class WorkspaceModel(Base):
    """Database representation of a workspace."""

    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    owner: Mapped[UserModel] = relationship(
        back_populates="owned_workspaces",
    )
    members: Mapped[list[WorkspaceMemberModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
