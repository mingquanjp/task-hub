"""Service layer for task management."""

import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from redis.asyncio import Redis

from taskhub.core.exceptions import (
    InvalidProjectStateError,
    TaskAssigneeNotWorkspaceMemberError,
    TaskNotFoundError,
)
from taskhub.modules.labels.repository import LabelRepository
from taskhub.modules.projects.entities import ProjectStatus
from taskhub.modules.projects.repository import ProjectRepository
from taskhub.modules.tasks.entities import Task, TaskPriority, TaskStatus
from taskhub.modules.tasks.repository import TaskRepository
from taskhub.modules.workspaces.repository import WorkspaceMemberRepository

logger = logging.getLogger(__name__)


class TaskService:
    """Business logic for task management."""

    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        label_repo: LabelRepository,
        workspace_member_repo: WorkspaceMemberRepository,
        redis: Redis | None = None,
        cache_ttl: int = 300,
    ) -> None:
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._label_repo = label_repo
        self._member_repo = workspace_member_repo
        self._redis = redis
        self._cache_ttl = cache_ttl

    async def _invalidate_project_cache(self, project_id: UUID) -> None:
        if self._redis:
            try:
                await self._redis.incr(f"task_list_version:{project_id}")
            except Exception:
                logger.warning(
                    "Redis cache invalidation failed",
                    exc_info=True,
                    extra={"project_id": str(project_id), "operation": "invalidate"},
                )

    async def _assert_project_active(self, project_id: UUID) -> None:
        """Ensure the project exists and is active."""
        # Project existence is mostly checked via router dependencies, but we verify state here
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            # We use ValueError or generic since Router dependencies should handle 404s
            # for projects. But just in case:
            from taskhub.core.exceptions import ProjectNotFoundError

            raise ProjectNotFoundError(f"Project {project_id} not found")

        if project.status == ProjectStatus.ARCHIVED:
            raise InvalidProjectStateError("Cannot modify tasks in an archived project")

    async def _assert_valid_assignee(self, project_id: UUID, assignee_id: UUID) -> None:
        """Ensure the assignee is a valid member of the project's workspace."""
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            from taskhub.core.exceptions import ProjectNotFoundError

            raise ProjectNotFoundError(f"Project {project_id} not found")

        member = await self._member_repo.get(project.workspace_id, assignee_id)
        if not member:
            raise TaskAssigneeNotWorkspaceMemberError(
                f"User {assignee_id} is not a member of the workspace"
            )

    async def create(
        self,
        project_id: UUID,
        creator_id: UUID,
        title: str,
        description: str | None = None,
        assignee_id: UUID | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: datetime | None = None,
    ) -> Task:
        """Create a new task."""
        await self._assert_project_active(project_id)

        if assignee_id:
            await self._assert_valid_assignee(project_id, assignee_id)

        task = Task(
            id=uuid4(),
            project_id=project_id,
            assignee_id=assignee_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            due_date=due_date,
            created_by=creator_id,
            created_at=datetime.now(UTC),
        )
        created_task = await self._task_repo.create(task)
        await self._invalidate_project_cache(project_id)
        return created_task

    async def get_by_id(self, task_id: UUID) -> Task:
        """Get a task by ID."""
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task

    async def update(
        self,
        task_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee_id: UUID | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        due_date: datetime | None = None,
        description_is_set: bool = False,
        assignee_id_is_set: bool = False,
        due_date_is_set: bool = False,
    ) -> Task:
        """Update an existing task."""
        task = await self.get_by_id(task_id)

        # Determine if we can modify the task
        await self._assert_project_active(task.project_id)

        if assignee_id_is_set and assignee_id is not None:
            await self._assert_valid_assignee(task.project_id, assignee_id)

        if title is not None:
            task.title = title
        if description_is_set:
            task.description = description
        if assignee_id_is_set:
            task.assignee_id = assignee_id
        if status is not None:
            task.status = status
        if priority is not None:
            task.priority = priority
        if due_date_is_set:
            task.due_date = due_date

        updated_task = await self._task_repo.update(task)
        await self._invalidate_project_cache(task.project_id)
        return updated_task

    async def delete(self, task_id: UUID) -> None:
        """Delete a task."""
        task = await self.get_by_id(task_id)

        # Policy note: We don't restrict deleting tasks in archived projects?
        # The prompt says "Delete task xử lý theo policy đã thống nhất".
        # For projects, archive is read-only. We'll enforce it.
        await self._assert_project_active(task.project_id)

        await self._task_repo.delete(task_id)
        await self._invalidate_project_cache(task.project_id)

    async def attach_label(self, task_id: UUID, label_id: UUID) -> None:
        """Attach a label to a task."""
        task = await self.get_by_id(task_id)
        await self._assert_project_active(task.project_id)

        label = await self._label_repo.get_by_id(label_id)
        if not label:
            from taskhub.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError(f"Label {label_id} not found")

        if label.project_id != task.project_id:
            from taskhub.core.exceptions import LabelProjectMismatchError

            raise LabelProjectMismatchError("Label belongs to a different project")

        await self._task_repo.attach_label(task_id, label_id)
        await self._invalidate_project_cache(task.project_id)

    async def detach_label(self, task_id: UUID, label_id: UUID) -> None:
        """Detach a label from a task."""
        task = await self.get_by_id(task_id)
        await self._assert_project_active(task.project_id)

        await self._task_repo.detach_label(task_id, label_id)
        await self._invalidate_project_cache(task.project_id)

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[Sequence[Task], int]:
        """List tasks within a project."""
        if page < 1:
            raise ValueError("Page must be >= 1")
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")

        offset = (page - 1) * limit

        if self._redis:
            try:
                version = await self._redis.get(f"task_list_version:{project_id}")
                if not version:
                    version_str = "1"
                    await self._redis.set(f"task_list_version:{project_id}", version_str)
                else:
                    version_str = (
                        version.decode("utf-8") if isinstance(version, bytes) else str(version)
                    )

                status_str = status.value if status else "any"
                priority_str = priority.value if priority else "any"
                assignee_str = str(assignee_id) if assignee_id else "any"

                cache_key = f"tasks:{project_id}:v{version_str}:{status_str}:{priority_str}:{assignee_str}:{page}:{limit}"
                cached_data = await self._redis.get(cache_key)

                if cached_data:
                    parsed = json.loads(cached_data)
                    tasks = []
                    for t_dict in parsed["tasks"]:
                        tasks.append(
                            Task(
                                id=UUID(t_dict["id"]),
                                project_id=UUID(t_dict["project_id"]),
                                assignee_id=UUID(t_dict["assignee_id"])
                                if t_dict.get("assignee_id")
                                else None,
                                title=t_dict["title"],
                                description=t_dict.get("description"),
                                status=TaskStatus(t_dict["status"]),
                                priority=TaskPriority(t_dict["priority"]),
                                due_date=datetime.fromisoformat(t_dict["due_date"])
                                if t_dict.get("due_date")
                                else None,
                                created_by=UUID(t_dict["created_by"]),
                                created_at=datetime.fromisoformat(t_dict["created_at"]),
                            )
                        )
                    return tasks, parsed["total"]
            except Exception:
                logger.warning(
                    "Redis cache get failed",
                    exc_info=True,
                    extra={"project_id": str(project_id), "operation": "get"},
                )

        db_tasks, total = await self._task_repo.list_by_project(
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            offset=offset,
            limit=limit,
        )

        if self._redis:
            try:
                tasks_dict = [
                    {
                        "id": str(t.id),
                        "project_id": str(t.project_id),
                        "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                        "title": t.title,
                        "description": t.description,
                        "status": t.status.value,
                        "priority": t.priority.value,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "created_by": str(t.created_by),
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in db_tasks
                ]
                await self._redis.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps({"tasks": tasks_dict, "total": total}),
                )
            except Exception:
                logger.warning(
                    "Redis cache set failed",
                    exc_info=True,
                    extra={"project_id": str(project_id), "operation": "set"},
                )

        return db_tasks, total
