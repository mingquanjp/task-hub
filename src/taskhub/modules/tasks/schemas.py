"""Pydantic schemas for the tasks module."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from taskhub.modules.tasks.entities import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
    ] = Field(..., description="Title of the task")
    description: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] = Field(None, description="Optional task description")
    assignee_id: UUID | None = Field(None, description="Optional assignee user ID")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: datetime | None = Field(None, description="Optional due date")


class TaskUpdate(BaseModel):
    """Schema for partially updating a task."""

    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
    ] | None = Field(None, description="Title of the task")
    description: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=2000)
    ] | None = Field(None, description="Optional task description")
    assignee_id: UUID | None = Field(None, description="Optional assignee user ID")
    status: TaskStatus | None = Field(None, description="Task status")
    priority: TaskPriority | None = Field(None, description="Task priority")
    due_date: datetime | None = Field(None, description="Optional due date")


class TaskResponse(BaseModel):
    """Schema for a task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    assignee_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_by: UUID
    created_at: datetime
