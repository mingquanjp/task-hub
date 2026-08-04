"""Pydantic schemas for projects."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from taskhub.modules.projects.entities import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)] = Field(
        ..., description="Name of the project"
    )
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = Field(
        None, description="Optional project description"
    )

    model_config = ConfigDict(extra="forbid")


class ProjectUpdate(BaseModel):
    """Schema for partially updating a project."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)] | None = Field(
        None, description="Name of the project"
    )
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] | None = Field(
        None, description="Optional project description"
    )

    model_config = ConfigDict(extra="forbid")


class ProjectResponse(BaseModel):
    """Schema for returning a project."""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
