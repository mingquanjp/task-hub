"""Schemas for comment payloads and responses."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class CommentCreate(BaseModel):
    """Schema for creating a new comment."""

    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
    ] = Field(..., description="Content of the comment")

    model_config = ConfigDict(extra="forbid")


class CommentUpdate(BaseModel):
    """Schema for partially updating a comment."""

    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
    ] = Field(..., description="New content of the comment")

    model_config = ConfigDict(extra="forbid")


class CommentResponse(BaseModel):
    """Schema for returning a comment."""

    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
