"""Pydantic schemas for Workspace API endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from taskhub.modules.workspaces.entities import WorkspaceRole


class WorkspaceCreate(BaseModel):
    """Schema for creating a new workspace."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    model_config = ConfigDict(extra="forbid")


class WorkspaceResponse(BaseModel):
    """Schema for a workspace response."""

    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberInvite(BaseModel):
    """Schema for inviting a user to a workspace."""

    user_id: UUID
    role: WorkspaceRole = Field(description="Must be EDITOR or VIEWER")

    model_config = ConfigDict(extra="forbid")


class WorkspaceMemberResponse(BaseModel):
    """Schema for a workspace member response."""

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDetailResponse(WorkspaceResponse):
    """Schema for a workspace with its members."""

    members: list[WorkspaceMemberResponse]

    model_config = ConfigDict(from_attributes=True)
