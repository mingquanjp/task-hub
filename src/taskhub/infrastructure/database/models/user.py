"""SQLAlchemy model for TaskHub users."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.infrastructure.database.base import Base
from taskhub.modules.auth.entities import UserRole

if TYPE_CHECKING:
    from taskhub.infrastructure.database.models.refresh_token import RefreshTokenModel
    from taskhub.infrastructure.database.models.workspace import WorkspaceModel
    from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel


class UserModel(Base):
    """Database representation of an authenticated user."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('ADMIN', 'MEMBER')", name="role_valid"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, create_constraint=False, length=6),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    owned_workspaces: Mapped[list[WorkspaceModel]] = relationship(
        back_populates="owner",
    )
    workspace_memberships: Mapped[list[WorkspaceMemberModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
