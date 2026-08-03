"""FastAPI dependency wiring for task use cases."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path

from taskhub.api.dependencies import DbSessionDep
from taskhub.core.exceptions import ResourceNotFoundError
from taskhub.modules.auth.dependencies import CurrentUserDep
from taskhub.modules.auth.entities import User
from taskhub.modules.projects.dependencies import (
    ProjectRepositoryDep,
    require_project_member,
    require_project_role,
)
from taskhub.modules.projects.entities import Project
from taskhub.modules.tasks.entities import Task
from taskhub.modules.tasks.repository import TaskRepository
from taskhub.modules.tasks.service import TaskService
from taskhub.modules.tasks.sqlalchemy_repository import SQLAlchemyTaskRepository
from taskhub.modules.workspaces.dependencies import (
    WorkspaceMemberRepositoryDep,
    WorkspaceRepositoryDep,
)
from taskhub.modules.workspaces.entities import WorkspaceRole


def get_task_repository(session: DbSessionDep) -> TaskRepository:
    """Provide the task repository."""
    return SQLAlchemyTaskRepository(session)


TaskRepositoryDep = Annotated[TaskRepository, Depends(get_task_repository)]


def get_task_service(
    task_repo: TaskRepositoryDep,
    project_repo: ProjectRepositoryDep,
    member_repo: WorkspaceMemberRepositoryDep,
) -> TaskService:
    """Provide the task service."""
    return TaskService(task_repo, project_repo, member_repo)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


async def get_task_or_404(
    task_id: Annotated[UUID, Path(...)],
    task_repo: TaskRepositoryDep,
) -> Task:
    """Get a task by ID or raise a 404."""
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise ResourceNotFoundError(f"Task {task_id} not found")
    return task


TaskDep = Annotated[Task, Depends(get_task_or_404)]


async def require_task_member(
    user: CurrentUserDep,
    task: TaskDep,
    project_repo: ProjectRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
    member_repo: WorkspaceMemberRepositoryDep,
) -> tuple[User, Task, Project]:
    """Ensure the user is a member of the project's workspace (or an ADMIN)."""
    project = await project_repo.get_by_id(task.project_id)
    if not project:
        from taskhub.core.exceptions import TaskProjectNotFoundError
        raise TaskProjectNotFoundError("Project for this task not found")
        
    await require_project_member(user, project, workspace_repo, member_repo)
    return user, task, project


TaskMemberDep = Annotated[tuple[User, Task, Project], Depends(require_task_member)]


def require_task_role(
    *allowed_roles: WorkspaceRole,
) -> Callable[..., Awaitable[tuple[User, Task, Project]]]:
    """
    Create a dependency that requires the user to have one of the specified
    roles in the task's project.
    """

    async def _require_role(
        user: CurrentUserDep,
        task: TaskDep,
        project_repo: ProjectRepositoryDep,
        workspace_repo: WorkspaceRepositoryDep,
        member_repo: WorkspaceMemberRepositoryDep,
    ) -> tuple[User, Task, Project]:
        project = await project_repo.get_by_id(task.project_id)
        if not project:
            from taskhub.core.exceptions import TaskProjectNotFoundError
            raise TaskProjectNotFoundError("Project for this task not found")
            
        dep = require_project_role(*allowed_roles)
        await dep(user, project, workspace_repo, member_repo)
        
        return user, task, project

    return _require_role


OwnerOrEditorTaskUserDep = Annotated[
    tuple[User, Task, Project],
    Depends(require_task_role(WorkspaceRole.OWNER, WorkspaceRole.EDITOR)),
]

OwnerTaskUserDep = Annotated[
    tuple[User, Task, Project],
    Depends(require_task_role(WorkspaceRole.OWNER)),
]
