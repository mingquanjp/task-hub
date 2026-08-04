"""HTTP endpoints for projects."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status

from taskhub.api.schemas import ErrorResponse
from taskhub.modules.projects.dependencies import (
    OwnerOrEditorProjectUserDep,
    OwnerProjectUserDep,
    ProjectMemberDep,
    ProjectServiceDep,
)
from taskhub.modules.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from taskhub.modules.workspaces.dependencies import (
    OwnerOrEditorWorkspaceUserDep,
    WorkspaceMemberUserDep,
)

# Router for paths prefixed with /projects
router = APIRouter(prefix="/projects", tags=["projects"])

# Router for paths prefixed with /workspaces/{workspace_id}/projects
workspace_projects_router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects", tags=["projects"]
)


@workspace_projects_router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def create_project(
    user: OwnerOrEditorWorkspaceUserDep,
    workspace_id: Annotated[UUID, Path(...)],
    data: ProjectCreate,
    service: ProjectServiceDep,
) -> ProjectResponse:
    """Create a new project within a workspace."""
    project = await service.create(workspace_id, data.name, data.description)
    return ProjectResponse.model_validate(project)


@workspace_projects_router.get(
    "",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
    },
)
async def list_projects(
    user: WorkspaceMemberUserDep,
    workspace_id: Annotated[UUID, Path(...)],
    service: ProjectServiceDep,
) -> list[ProjectResponse]:
    """List all projects within a workspace."""
    projects = await service.list_by_workspace(workspace_id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def get_project(
    user_project: ProjectMemberDep,
    project_id: Annotated[UUID, Path(...)],
) -> ProjectResponse:
    """Get a project by ID."""
    _, project = user_project
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Conflict or Invalid State"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
    },
)
async def update_project(
    user_project: OwnerOrEditorProjectUserDep,
    project_id: Annotated[UUID, Path(...)],
    data: ProjectUpdate,
    service: ProjectServiceDep,
) -> ProjectResponse:
    """Update a project partially."""
    description_is_set = "description" in data.model_fields_set

    project = await service.update(
        project_id,
        name=data.name,
        description=data.description,
        description_is_set=description_is_set,
    )
    return ProjectResponse.model_validate(project)


@router.post(
    "/{project_id}/archive",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        409: {"model": ErrorResponse, "description": "Already archived"},
    },
)
async def archive_project(
    user_project: OwnerOrEditorProjectUserDep,
    project_id: Annotated[UUID, Path(...)],
    service: ProjectServiceDep,
) -> ProjectResponse:
    """Archive a project."""
    project = await service.archive(project_id)
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project not found"},
    },
)
async def delete_project(
    user_project: OwnerProjectUserDep,
    project_id: Annotated[UUID, Path(...)],
    service: ProjectServiceDep,
) -> None:
    """Delete a project (Owner and Admin only)."""
    await service.delete(project_id)
