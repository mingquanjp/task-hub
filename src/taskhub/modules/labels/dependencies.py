"""FastAPI dependency wiring for label use cases."""

from typing import Annotated

from fastapi import Depends

from taskhub.api.dependencies import DbSessionDep, get_db_session  # noqa: F401
from taskhub.modules.labels.repository import LabelRepository
from taskhub.modules.labels.service import LabelService
from taskhub.modules.labels.sqlalchemy_repository import SQLAlchemyLabelRepository


def get_label_repository(session: DbSessionDep) -> LabelRepository:
    """Build the runtime label repository from the request database session."""
    return SQLAlchemyLabelRepository(session)


LabelRepositoryDep = Annotated[LabelRepository, Depends(get_label_repository)]


def get_label_service(repository: LabelRepositoryDep) -> LabelService:
    """Build the label service from its persistence dependency."""
    return LabelService(repository)


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
