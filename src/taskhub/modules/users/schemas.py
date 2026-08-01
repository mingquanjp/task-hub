"""Pydantic schemas for users HTTP contracts."""

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserProfileUpdate(BaseModel):
    """Fields that can be updated on a user profile."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "email" in data and data["email"] is None:
                raise ValueError("email cannot be null")
            if "full_name" in data and data["full_name"] is None:
                raise ValueError("full_name cannot be null")
        return data

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> EmailStr | None:
        if value is not None:
            return str(value).strip().lower()
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = " ".join(value.split())
            if not normalized:
                raise ValueError("full_name must not be blank")
            return normalized
        return value


class ChangePasswordRequest(BaseModel):
    """Credentials required to change a user's password."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("new_password must not be blank")
        return value
