"""FastAPI dependency wiring for label use cases."""

from typing import Annotated, cast

from fastapi import Depends, Request

from taskhub.modules.labels.repository import LabelRepository
from taskhub.modules.labels.service import LabelService


def get_label_repository(request: Request) -> LabelRepository:
    """Return the application-scoped label repository."""
    return cast(LabelRepository, request.app.state.label_repository)


LabelRepositoryDep = Annotated[LabelRepository, Depends(get_label_repository)]


def get_label_service(repository: LabelRepositoryDep) -> LabelService:
    """Build the label service from its persistence dependency."""
    return LabelService(repository)


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
