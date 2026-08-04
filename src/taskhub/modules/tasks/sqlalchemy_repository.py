"""SQLAlchemy implementation of the task repository."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.infrastructure.database.models.task import TaskModel
from taskhub.infrastructure.database.models.task_label import TaskLabelModel
from taskhub.infrastructure.repositories.base import BaseRepository
from taskhub.modules.tasks.entities import Task, TaskPriority, TaskStatus
from taskhub.modules.tasks.repository import TaskRepository


class SQLAlchemyTaskRepository(TaskRepository):
    """SQLAlchemy implementation of TaskRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._models = BaseRepository(session, TaskModel)

    def _to_domain(self, model: TaskModel) -> Task:
        """Map ORM model to domain entity."""
        return Task(
            id=model.id,
            project_id=model.project_id,
            assignee_id=model.assignee_id,
            title=model.title,
            description=model.description,
            status=TaskStatus(model.status),
            priority=TaskPriority(model.priority),
            due_date=model.due_date,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    def _to_model(self, task: Task) -> TaskModel:
        """Map domain entity to ORM model."""
        return TaskModel(
            id=task.id,
            project_id=task.project_id,
            assignee_id=task.assignee_id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            priority=task.priority.value,
            due_date=task.due_date,
            created_by=task.created_by,
            created_at=task.created_at,
        )

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        model = self._to_model(task)
        await self._models.add(model)
        return self._to_domain(model)

    async def get_by_id(self, task_id: UUID) -> Task | None:
        """Get a task by its ID."""
        model = await self._models.get_by_id(task_id)
        if not model:
            return None
        return self._to_domain(model)

    async def update(self, task: Task) -> Task:
        """Update an existing task."""
        model = await self._models.get_by_id(task.id)
        if not model:
            raise ValueError(f"Task {task.id} not found in database")

        model.title = task.title
        model.description = task.description
        model.assignee_id = task.assignee_id
        model.status = task.status.value
        model.priority = task.priority.value
        model.due_date = task.due_date

        await self._session.flush()
        return self._to_domain(model)

    async def delete(self, task_id: UUID) -> None:
        """Delete a task."""
        model = await self._models.get_by_id(task_id)
        if model:
            await self._models.delete(model)

    async def attach_label(self, task_id: UUID, label_id: UUID) -> None:
        """Attach a label to a task."""
        from sqlalchemy.exc import IntegrityError

        from taskhub.core.exceptions import TaskLabelAlreadyExistsError

        stmt = insert(TaskLabelModel).values(task_id=task_id, label_id=label_id)
        try:
            await self._session.execute(stmt)
        except IntegrityError as err:
            raise TaskLabelAlreadyExistsError("Label is already attached to this task") from err

    async def detach_label(self, task_id: UUID, label_id: UUID) -> None:
        """Detach a label from a task."""

        stmt = delete(TaskLabelModel).where(
            TaskLabelModel.task_id == task_id, TaskLabelModel.label_id == label_id
        )
        await self._session.execute(stmt)

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
        """List tasks with filtering and pagination."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if limit > 100:
            raise ValueError("limit must not exceed 100")

        # Build base filter
        filters: list[Any] = [TaskModel.project_id == project_id]
        if status:
            filters.append(TaskModel.status == status.value)
        if priority:
            filters.append(TaskModel.priority == priority.value)
        if assignee_id:
            filters.append(TaskModel.assignee_id == assignee_id)

        # Count total
        count_stmt = select(func.count()).select_from(TaskModel).where(*filters)
        total = await self._session.scalar(count_stmt) or 0

        # Query items
        stmt = (
            select(TaskModel)
            .where(*filters)
            .order_by(TaskModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        tasks = [self._to_domain(model) for model in result.all()]

        return tasks, total
