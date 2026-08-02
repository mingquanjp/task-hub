"""Import ORM models so Alembic can discover their table metadata."""

from taskhub.infrastructure.database.models.label import LabelModel
from taskhub.infrastructure.database.models.project import ProjectModel
from taskhub.infrastructure.database.models.refresh_token import RefreshTokenModel
from taskhub.infrastructure.database.models.user import UserModel
from taskhub.infrastructure.database.models.workspace import WorkspaceModel
from taskhub.infrastructure.database.models.workspace_member import WorkspaceMemberModel
from taskhub.modules.auth.entities import UserRole

__all__ = [
    "LabelModel",
    "ProjectModel",
    "RefreshTokenModel",
    "UserModel",
    "UserRole",
    "WorkspaceMemberModel",
    "WorkspaceModel",
]
