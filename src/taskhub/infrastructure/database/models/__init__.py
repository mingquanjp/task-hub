"""Import ORM models so Alembic can discover their table metadata."""

from taskhub.infrastructure.database.models.label import LabelModel
from taskhub.infrastructure.database.models.project import ProjectModel

__all__ = ["LabelModel", "ProjectModel"]
