"""Pydantic schemas for authentication HTTP contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from taskhub.modules.auth.entities import UserRole


class RegisterRequest(BaseModel):
    """Credentials and profile fields required to register a user."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("password must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("full_name must not be blank")
        return normalized


class LoginRequest(BaseModel):
    """Credentials used to authenticate a user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return str(value).strip().lower()


class RefreshTokenRequest(BaseModel):
    """A refresh token presented for rotation or revocation."""

    refresh_token: str = Field(min_length=1, max_length=4096)


class UserResponse(BaseModel):
    """Public user representation; password material is intentionally absent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Access and rotated refresh credentials returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
