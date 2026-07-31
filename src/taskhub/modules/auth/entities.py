"""Framework-independent authentication entities."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class UserRole(StrEnum):
    """System-level role used for administrative authorization."""

    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


@dataclass(frozen=True, slots=True)
class User:
    """Domain representation of an authenticated user."""

    id: UUID
    email: str
    full_name: str
    hashed_password: str
    role: UserRole
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """Domain representation of persisted refresh-token state."""

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
