"""Pydantic schemas for projects."""

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from taskhub.modules.projects.entities import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)] = (
        Field(..., description="Name of the project")
    )
    description: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = Field(None, description="Optional project description")

    model_config = ConfigDict(extra="forbid")


class ProjectUpdate(BaseModel):
    """Schema for partially updating a project."""

    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
        | None
    ) = Field(None, description="Name of the project")
    description: (
        Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = Field(None, description="Optional project description")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_partial_update(self) -> Self:
        """Require at least one field for an update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for an update")
        return self


class ProjectResponse(BaseModel):
    """Schema for returning a project."""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
