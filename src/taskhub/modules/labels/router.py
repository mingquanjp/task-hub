"""HTTP endpoints for project labels."""

from uuid import UUID

from fastapi import APIRouter, Response, status

from taskhub.modules.labels.dependencies import LabelServiceDep
from taskhub.modules.labels.schemas import LabelCreate, LabelResponse, LabelUpdate

router = APIRouter(prefix="/projects/{project_id}/labels", tags=["labels"])


@router.post(
    "",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Project not found"}},
)
async def create_label(
    project_id: UUID,
    data: LabelCreate,
    service: LabelServiceDep,
) -> LabelResponse:
    """Create a label in a project."""
    return LabelResponse.model_validate(await service.create(project_id, data))


@router.get("", response_model=list[LabelResponse])
async def list_labels(project_id: UUID, service: LabelServiceDep) -> list[LabelResponse]:
    """List labels in a project."""
    return [
        LabelResponse.model_validate(label) for label in await service.list_by_project(project_id)
    ]


@router.get(
    "/{label_id}",
    response_model=LabelResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Label not found"}},
)
async def get_label(
    project_id: UUID,
    label_id: UUID,
    service: LabelServiceDep,
) -> LabelResponse:
    """Get a label in a project."""
    return LabelResponse.model_validate(await service.get(project_id, label_id))


@router.patch(
    "/{label_id}",
    response_model=LabelResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Label not found"}},
)
async def update_label(
    project_id: UUID,
    label_id: UUID,
    data: LabelUpdate,
    service: LabelServiceDep,
) -> LabelResponse:
    """Partially update a label in a project."""
    return LabelResponse.model_validate(await service.update(project_id, label_id, data))


@router.delete(
    "/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Label not found"}},
)
async def delete_label(project_id: UUID, label_id: UUID, service: LabelServiceDep) -> Response:
    """Delete a label in a project."""
    await service.delete(project_id, label_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
