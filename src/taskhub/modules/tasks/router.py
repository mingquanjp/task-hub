"""HTTP endpoints for tasks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from taskhub.api.schemas import ErrorResponse, PaginatedResponse
from taskhub.modules.projects.dependencies import (
    OwnerOrEditorProjectUserDep,
    ProjectMemberDep,
)
from taskhub.modules.tasks.dependencies import (
    OwnerOrEditorTaskUserDep,
    TaskMemberDep,
    TaskServiceDep,
)
from taskhub.modules.tasks.entities import TaskPriority, TaskStatus
from taskhub.modules.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate

# Router for paths prefixed with /tasks
router = APIRouter(prefix="/tasks", tags=["tasks"])

# Router for paths prefixed with /projects/{project_id}/tasks
project_tasks_router = APIRouter(
    prefix="/projects/{project_id}/tasks", tags=["tasks"]
)


@project_tasks_router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project or Assignee not found"},
        409: {"model": ErrorResponse, "description": "Conflict or Invalid State"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def create_task(
    user_project: OwnerOrEditorProjectUserDep,
    project_id: Annotated[UUID, Path(...)],
    data: TaskCreate,
    service: TaskServiceDep,
) -> TaskResponse:
    """Create a new task within a project."""
    user, project = user_project
    task = await service.create(
        project_id=project_id,
        creator_id=user.id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        priority=data.priority,
        due_date=data.due_date,
    )
    return TaskResponse.model_validate(task)


@project_tasks_router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def list_tasks(
    user_project: ProjectMemberDep,
    project_id: Annotated[UUID, Path(...)],
    service: TaskServiceDep,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority_filter: Annotated[TaskPriority | None, Query(alias="priority")] = None,
    assignee_id: Annotated[UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedResponse[TaskResponse]:
    """List tasks within a project with optional filtering and pagination."""
    tasks, total = await service.list_by_project(
        project_id=project_id,
        status=status_filter,
        priority=priority_filter,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )
    items = [TaskResponse.model_validate(t) for t in tasks]
    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
)
async def get_task(
    user_task_project: TaskMemberDep,
    task_id: Annotated[UUID, Path(...)],
) -> TaskResponse:
    """Get a task by ID."""
    _, task, _ = user_task_project
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Task or Assignee not found"},
        409: {"model": ErrorResponse, "description": "Conflict or Invalid State"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def update_task(
    user_task_project: OwnerOrEditorTaskUserDep,
    task_id: Annotated[UUID, Path(...)],
    data: TaskUpdate,
    service: TaskServiceDep,
) -> TaskResponse:
    """Update a task partially."""
    if not data.model_fields_set:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Empty request body")

    task = await service.update(
        task_id=task_id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        description_is_set="description" in data.model_fields_set,
        assignee_id_is_set="assignee_id" in data.model_fields_set,
        due_date_is_set="due_date" in data.model_fields_set,
    )
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
)
async def delete_task(
    user_task_project: OwnerOrEditorTaskUserDep,  # As per prompt, Owner or Editor
    task_id: Annotated[UUID, Path(...)],
    service: TaskServiceDep,
) -> None:
    """Delete a task."""
    await service.delete(task_id)
