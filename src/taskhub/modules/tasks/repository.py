"""Task repository interface."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from taskhub.modules.tasks.entities import Task, TaskPriority, TaskStatus


class TaskRepository(Protocol):
    """Data access contract for tasks."""

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        ...

    async def get_by_id(self, task_id: UUID) -> Task | None:
        """Get a task by its ID."""
        ...

    async def update(self, task: Task) -> Task:
        """Update an existing task."""
        ...

    async def delete(self, task_id: UUID) -> None:
        """Delete a task."""
        ...

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Task], int]:
        """
        List tasks in a project with optional filtering and pagination.
        
        Returns:
            A tuple of (tasks, total_count).
        """
        ...
