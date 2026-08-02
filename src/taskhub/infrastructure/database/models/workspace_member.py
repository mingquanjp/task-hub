"""SQLAlchemy model for TaskHub workspace memberships."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base
from taskhub.modules.workspaces.entities import WorkspaceRole

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.user import UserModel
    from taskhub.infrastructure.database.models.workspace import WorkspaceModel


class WorkspaceMemberModel(Base):
    """Database representation of a user's membership in a workspace."""

    __tablename__ = "workspace_members"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        SAEnum(WorkspaceRole, native_enum=False, create_constraint=True, length=10),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    workspace: Mapped[WorkspaceModel] = relationship(
        back_populates="members",
    )
    user: Mapped[UserModel] = relationship(
        back_populates="workspace_memberships",
    )
